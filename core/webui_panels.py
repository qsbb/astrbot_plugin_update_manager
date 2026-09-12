"""series.webui@1.0 面板契约网关：独立 WebUI 统一接管各插件管理面。

设计要点（结合系列既有经验）：
- 与 series_control 相同的信任边界：只接受可信登记（TRUSTED_BY_ID）中的
  插件，契约四要素（name/plugin_id/series_id/panels）校验失败一律
  fail-closed，绝不执行未声明面板或动作。
- 面板数据与动作全部走 in-process 调用（adapter.get_plugin_instance），
  不经 HTTP、不依赖 dashboard 会话；写操作由 WebUI 会话角色门控
  （admin 及以上），动作本身还可通过 payload 二次校验。
- 面板返回通用渲染契约：columns/rows/actions，前端无需为每个插件
  定制 UI 即可完成统一接管。
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import inspect
import re
from typing import Any, Mapping

from ..series_diagnostics import diagnostic_event
from .adapters.astrbot import AstrBotAdapter
from .trusted import DIAGNOSTIC_SERIES_ID, TRUSTED_BY_ID

CONTRACT_NAME = "series.webui@1.0"
CONTRACT_NAMES = {
    "series.webui@1.0",
    "series.webui@1.1",
    "series.webui@2.0",
}
SUPPORTED_CAPABILITIES = {
    "revision",
    "idempotency",
    "generic_table",
    "generic_actions",
    "file_upload",
    "artifacts",
    "audio_preview",
    "jobs",
    "sse",
}
CONTRACT_CALL_TIMEOUT_SECONDS = 3.0

PANEL_ROLES = {"viewer": 0, "admin": 1, "owner": 2}

_ALLOWED_PANEL_ID = re.compile(r"^[a-z0-9_]{1,48}$")
_ALLOWED_ACTION_ID = re.compile(r"^[a-z0-9_]{1,48}$")


class WebUIPanelsGateway:
    """把可信插件的 webui 面板契约安全地暴露给独立 WebUI。"""

    def __init__(self, adapter: AstrBotAdapter) -> None:
        self.adapter = adapter

    @staticmethod
    def _canonical(plugin_id: str) -> str:
        trusted = TRUSTED_BY_ID.get(str(plugin_id))
        if trusted is None:
            raise LookupError("PLUGIN_NOT_TRUSTED")
        return trusted.plugin_id

    async def _instance(self, plugin_id: str) -> tuple[str, Any, Mapping[str, Any]]:
        canonical = self._canonical(plugin_id)
        getter = getattr(self.adapter, "get_plugin_instance", None)
        if not callable(getter):
            raise LookupError("PLUGIN_NOT_LOADED")
        instance = await _maybe_await(getter(canonical))
        if instance is None and canonical != plugin_id:
            instance = await _maybe_await(getter(plugin_id))
        if instance is None:
            raise LookupError("PLUGIN_NOT_LOADED")
        contract = await _maybe_await_call(instance, "webui_panels_contract")
        if (
            not isinstance(contract, Mapping)
            or contract.get("name") not in CONTRACT_NAMES
        ):
            raise LookupError("CONTRACT_UNAVAILABLE")
        if str(contract.get("series_id")) != DIAGNOSTIC_SERIES_ID:
            raise LookupError("CONTRACT_VERSION_UNSUPPORTED")
        if str(contract.get("plugin_id")) not in {canonical, plugin_id}:
            raise LookupError("CONTRACT_VERSION_UNSUPPORTED")
        version = contract.get("version")
        # 兼容旧契约缺失 version；显式声明时只接受 1.x。
        if version not in (None, "", "1", "1.0", "1.1", "2.0", 1, 1.0, 1.1, 2.0):
            raise LookupError("CONTRACT_VERSION_UNSUPPORTED")
        if not _declared_panels(contract):
            raise LookupError("CONTRACT_UNAVAILABLE")
        return canonical, instance, contract

    async def panels(self, plugin_id: str) -> dict[str, Any]:
        canonical, _instance, contract = await self._instance(plugin_id)
        panels = _as_sequence(contract.get("panels"))
        panels = [
            {
                "id": str(item.get("id") or ""),
                "title": str(item.get("title") or item.get("id") or ""),
                "description": str(item.get("description") or ""),
            }
            for item in panels
            if isinstance(item, Mapping)
            and _ALLOWED_PANEL_ID.match(str(item.get("id") or ""))
        ]
        capabilities = _contract_capabilities(contract)
        unsupported = sorted(
            capability
            for capability in capabilities
            if capability not in SUPPORTED_CAPABILITIES
        )
        return {
            "plugin_id": canonical,
            "panels": panels,
            "capabilities": capabilities,
            "unsupported_capabilities": unsupported,
        }

    async def data(
        self,
        plugin_id: str,
        panel: str,
        *,
        artifact_writer: Any | None = None,
    ) -> dict[str, Any]:
        panel = _require_panel_id(panel)
        canonical, instance, contract = await self._instance(plugin_id)
        _require_declared_panel(contract, panel)
        payload = await _maybe_await_call(
            instance,
            "webui_panel_data",
            panel,
            timeout=CONTRACT_CALL_TIMEOUT_SECONDS,
        )
        if not isinstance(payload, Mapping):
            raise ValueError("PANEL_DATA_INVALID")
        if not isinstance(payload.get("success"), bool):
            payload = dict(payload)
            payload.setdefault("success", True)
        return _materialize_panel_artifacts(
            dict(payload),
            plugin_id=canonical,
            panel=panel,
            artifact_writer=artifact_writer,
        )

    async def action(
        self,
        plugin_id: str,
        panel: str,
        action: str,
        payload: Mapping[str, Any] | None,
        role: str = "",
        context: Mapping[str, Any] | None = None,
        *,
        artifact_reader: Any | None = None,
    ) -> dict[str, Any]:
        panel = _require_panel_id(panel)
        action = _require_action_id(action)
        if PANEL_ROLES.get(role, -1) < PANEL_ROLES["admin"]:
            raise PermissionError("ROLE_FORBIDDEN")
        canonical, instance, contract = await self._instance(plugin_id)
        declaration = _require_declared_action(contract, panel, action)
        context_dict = dict(context) if isinstance(context, Mapping) else {}
        _validate_action_context(declaration, role, context_dict)
        if not isinstance(payload, Mapping):
            payload = {}
        normalized_payload = await _resolve_declared_artifacts(
            dict(payload),
            declaration=declaration,
            plugin_id=canonical,
            panel=panel,
            artifact_reader=artifact_reader,
        )
        result = await _maybe_await_call_action(
            instance,
            panel,
            action,
            normalized_payload,
            context_dict,
            timeout=CONTRACT_CALL_TIMEOUT_SECONDS,
        )
        if not isinstance(result, Mapping):
            raise ValueError("PANEL_ACTION_INVALID")
        try:
            diagnostic_event(
                "webui.panel.action",
                "WebUI 面板动作",
                details={
                    "plugin_id": canonical,
                    "panel": panel,
                    "action": action,
                    "role": role,
                    "request_id": str(context_dict.get("request_id") or ""),
                    "effect": str(declaration.get("effect") or "idempotent")
                    if isinstance(declaration, Mapping)
                    else "dynamic",
                },
            )
        except Exception:
            pass
        return dict(result)

    async def stream(
        self,
        plugin_id: str,
        panel: str,
        context: Mapping[str, Any] | None = None,
    ):
        """SSE 面板流：插件必须声明 sse 能力并实现 webui_panel_stream。"""
        panel = _require_panel_id(panel)
        _canonical, instance, contract = await self._instance(plugin_id)
        _require_declared_panel(contract, panel)
        if "sse" not in _contract_capabilities(contract):
            raise LookupError("CAPABILITY_UNAVAILABLE")
        function = getattr(instance, "webui_panel_stream", None)
        if not callable(function):
            raise LookupError("CONTRACT_UNAVAILABLE")
        context_dict = dict(context) if isinstance(context, Mapping) else {}
        try:
            signature = inspect.signature(function)
            accepts_context = (
                "context" in signature.parameters
                or any(
                    parameter.kind == inspect.Parameter.VAR_KEYWORD
                    for parameter in signature.parameters.values()
                )
            )
        except (TypeError, ValueError):
            accepts_context = False
        result = (
            function(panel, context=context_dict)
            if accepts_context
            else function(panel)
        )
        if inspect.isasyncgen(result):
            async for event in result:
                yield event
            return
        result = await _maybe_await(result)
        if isinstance(result, (list, tuple)):
            for event in result:
                yield event
            return
        if hasattr(result, "__aiter__"):
            async for event in result:
                yield event
            return
        yield result


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _maybe_await_call(
    instance: Any,
    method: str,
    *args: Any,
    timeout: float | None = CONTRACT_CALL_TIMEOUT_SECONDS,
    **kwargs: Any,
) -> Any:
    function = getattr(instance, method, None)
    if not callable(function):
        raise LookupError("CONTRACT_UNAVAILABLE")
    # 同步方法不能直接在 aiohttp 事件循环里执行；先生成可等待对象，
    # 再统一施加有界超时，避免卡死整个 WebUI。
    if inspect.iscoroutinefunction(function):
        awaitable = function(*args, **kwargs)
    else:
        awaitable = asyncio.to_thread(function, *args, **kwargs)
    if timeout is None or timeout <= 0:
        result = await awaitable
    else:
        result = await asyncio.wait_for(awaitable, timeout=timeout)
    if inspect.isawaitable(result):
        if timeout is None or timeout <= 0:
            result = await result
        else:
            result = await asyncio.wait_for(result, timeout=timeout)
    return result


def _contract_capabilities(contract: Mapping[str, Any]) -> list[str]:
    raw = contract.get("capabilities")
    if not isinstance(raw, (list, tuple, set)):
        return []
    return sorted(
        {str(item) for item in raw if isinstance(item, str) and item.strip()}
    )


def _as_sequence(value: Any) -> list[Any]:
    """契约字段既接受 JSON list，也接受历史 tuple 声明。"""
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


def _declared_panels(contract: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    declared: dict[str, Mapping[str, Any]] = {}
    for item in _as_sequence(contract.get("panels")):
        if not isinstance(item, Mapping):
            continue
        panel_id = str(item.get("id") or "")
        if _ALLOWED_PANEL_ID.match(panel_id):
            declared[panel_id] = item
    return declared


def _require_declared_panel(contract: Mapping[str, Any], panel: str) -> None:
    declared = _declared_panels(contract)
    if not declared or panel not in declared:
        raise ValueError("UNKNOWN_PANEL")


def _require_declared_action(
    contract: Mapping[str, Any], panel: str, action: str
) -> Mapping[str, Any]:
    declared = _declared_panels(contract)
    if not declared:
        raise ValueError("UNKNOWN_PANEL")
    panel_decl = declared.get(panel)
    if panel_decl is None:
        raise ValueError("UNKNOWN_PANEL")
    actions = _as_sequence(panel_decl.get("actions"))
    if not actions:
        return {}
    for item in actions:
        if isinstance(item, Mapping) and str(item.get("id") or "") == action:
            return item
    raise ValueError("UNKNOWN_ACTION")


def _validate_action_context(
    declaration: Mapping[str, Any], role: str, context: Mapping[str, Any]
) -> None:
    if not isinstance(declaration, Mapping):
        return
    min_role = str(declaration.get("min_role") or "admin")
    if PANEL_ROLES.get(role, -1) < PANEL_ROLES.get(min_role, PANEL_ROLES["admin"]):
        raise PermissionError("ROLE_FORBIDDEN")
    effect = str(declaration.get("effect") or "idempotent")
    if effect == "non_idempotent" and not str(context.get("request_id") or "").strip():
        raise ValueError("IDEMPOTENCY_REQUIRED")
    if bool(declaration.get("revision_required")) and context.get(
        "expected_revision"
    ) in (None, ""):
        raise ValueError("REVISION_REQUIRED")


async def _maybe_await_call_action(
    instance: Any,
    panel: str,
    action: str,
    payload: dict[str, Any],
    context: dict[str, Any],
    *,
    timeout: float | None = CONTRACT_CALL_TIMEOUT_SECONDS,
) -> Any:
    """调用 webui_panel_action；兼容不接受 context 的旧插件。"""
    function = getattr(instance, "webui_panel_action", None)
    if not callable(function):
        raise LookupError("CONTRACT_UNAVAILABLE")
    try:
        signature = inspect.signature(function)
        accepts_context = (
            "context" in signature.parameters
            or any(
                parameter.kind == inspect.Parameter.VAR_KEYWORD
                for parameter in signature.parameters.values()
            )
        )
    except (TypeError, ValueError):
        accepts_context = False
    if accepts_context:
        return await _maybe_await_call(
            instance,
            "webui_panel_action",
            panel,
            action,
            payload,
            context=context,
            timeout=timeout,
        )
    return await _maybe_await_call(
        instance,
        "webui_panel_action",
        panel,
        action,
        payload,
        timeout=timeout,
    )



async def _resolve_declared_artifacts(
    payload: dict[str, Any],
    *,
    declaration: Mapping[str, Any],
    plugin_id: str,
    panel: str,
    artifact_reader: Any | None,
) -> dict[str, Any]:
    """把动作里声明的 file 字段从 artifact_id 解析成标准制品描述。

    series.webui@2.0 的 file 字段由核 WebUI 先上传到 ArtifactStore，再在动作调用前
    解析为 ``{artifact_id, filename, mime, size, data}``。插件不接触核内部对象，也
    不需要读取上传临时路径。
    """
    fields = _as_sequence(declaration.get("payload_fields"))
    file_fields = [
        item
        for item in fields
        if isinstance(item, Mapping) and str(item.get("type") or "") == "file"
    ]
    if not file_fields:
        return payload
    if artifact_reader is None:
        raise ValueError("ARTIFACT_TRANSPORT_UNAVAILABLE")
    for field in file_fields:
        name = str(field.get("name") or "").strip()
        if not name or name not in payload:
            continue
        raw = payload.get(name)
        multiple = bool(field.get("multiple"))
        values = raw if multiple else [raw]
        if not isinstance(values, list):
            raise ValueError(f"INVALID_ARTIFACT_FIELD:{name}")
        if len(values) > 20:
            raise ValueError(f"TOO_MANY_ARTIFACTS:{name}")
        resolved: list[dict[str, Any]] = []
        for value in values:
            artifact_id = str(value or "").strip()
            if not artifact_id:
                if bool(field.get("required")):
                    raise ValueError(f"ARTIFACT_REQUIRED:{name}")
                continue
            try:
                item = artifact_reader(artifact_id, plugin_id, panel)
                if inspect.isawaitable(item):
                    item = await item
            except LookupError:
                raise
            except PermissionError:
                raise
            if not isinstance(item, Mapping):
                raise ValueError(f"ARTIFACT_NOT_FOUND:{name}")
            data = item.get("data")
            if not isinstance(data, (bytes, bytearray)):
                raise ValueError(f"ARTIFACT_CONTENT_INVALID:{name}")
            resolved.append(
                {
                    "artifact_id": str(item.get("artifact_id") or artifact_id),
                    "filename": str(item.get("filename") or "artifact.bin"),
                    "mime": str(item.get("mime") or "application/octet-stream"),
                    "size": len(data),
                    "data": bytes(data),
                }
            )
        payload[name] = resolved if multiple else (resolved[0] if resolved else None)
    return payload


def _materialize_panel_artifacts(
    payload: dict[str, Any],
    *,
    plugin_id: str,
    panel: str,
    artifact_writer: Any | None,
) -> dict[str, Any]:
    """把插件返回的 bytes/base64 制品写入核制品区，响应只携带短期 ID。"""
    for key in ("artifacts", "audio"):
        raw = payload.get(key)
        if raw is None:
            continue
        multiple = key == "artifacts"
        items = raw if isinstance(raw, list) else [raw]
        if multiple and not isinstance(raw, list):
            raise ValueError("ARTIFACT_OUTPUT_INVALID")
        rendered: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, Mapping):
                raise ValueError("ARTIFACT_OUTPUT_INVALID")
            descriptor = dict(item)
            if descriptor.get("artifact_id"):
                descriptor.pop("data", None)
                descriptor.pop("content_base64", None)
                rendered.append(descriptor)
                continue
            data = descriptor.pop("data", None)
            if data is None and isinstance(descriptor.get("content_base64"), str):
                try:
                    data = base64.b64decode(
                        descriptor.pop("content_base64"), validate=True
                    )
                except (ValueError, binascii.Error):
                    raise ValueError("ARTIFACT_CONTENT_INVALID")
            else:
                descriptor.pop("content_base64", None)
            if not isinstance(data, (bytes, bytearray)):
                raise ValueError("ARTIFACT_CONTENT_INVALID")
            if artifact_writer is None:
                raise ValueError("ARTIFACT_TRANSPORT_UNAVAILABLE")
            snapshot = artifact_writer(
                plugin_id,
                panel,
                filename=str(descriptor.get("filename") or "artifact.bin"),
                mime=str(descriptor.get("mime") or "application/octet-stream"),
                data=bytes(data),
            )
            if inspect.isawaitable(snapshot):
                # 制品写入由网关内部完成；此处保持纯函数接口，异步写入应在外层处理。
                raise ValueError("ARTIFACT_WRITER_ASYNC_UNSUPPORTED")
            if not isinstance(snapshot, Mapping):
                raise ValueError("ARTIFACT_WRITE_FAILED")
            descriptor.update(snapshot)
            rendered.append(descriptor)
        payload[key] = rendered if multiple else (rendered[0] if rendered else None)
    return payload

def _require_panel_id(panel: str) -> str:
    panel = str(panel or "")
    if not _ALLOWED_PANEL_ID.match(panel):
        raise ValueError("INVALID_PANEL_ID")
    return panel


def _require_action_id(action: str) -> str:
    action = str(action or "")
    if not _ALLOWED_ACTION_ID.match(action):
        raise ValueError("INVALID_ACTION_ID")
    return action
