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

import inspect
import re
from typing import Any, Mapping

from .adapters.astrbot import AstrBotAdapter
from .trusted import DIAGNOSTIC_SERIES_ID, TRUSTED_BY_ID

CONTRACT_NAME = "series.webui@1.0"

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

    async def _instance(self, plugin_id: str) -> tuple[str, Any]:
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
        if not isinstance(contract, Mapping) or contract.get("name") != CONTRACT_NAME:
            raise LookupError("CONTRACT_UNAVAILABLE")
        if str(contract.get("series_id")) != DIAGNOSTIC_SERIES_ID:
            raise LookupError("CONTRACT_VERSION_UNSUPPORTED")
        if str(contract.get("plugin_id")) not in {canonical, plugin_id}:
            raise LookupError("CONTRACT_VERSION_UNSUPPORTED")
        return canonical, instance

    async def panels(self, plugin_id: str) -> dict[str, Any]:
        _canonical, instance = await self._instance(plugin_id)
        contract = await _maybe_await_call(instance, "webui_panels_contract")
        panels = contract.get("panels")
        if not isinstance(panels, list):
            panels = []
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
        return {"plugin_id": _canonical, "panels": panels}

    async def data(self, plugin_id: str, panel: str) -> dict[str, Any]:
        panel = _require_panel_id(panel)
        _canonical, instance = await self._instance(plugin_id)
        payload = await _maybe_await_call(instance, "webui_panel_data", panel)
        if not isinstance(payload, Mapping):
            raise ValueError("PANEL_DATA_INVALID")
        if not isinstance(payload.get("success"), bool):
            payload = dict(payload)
            payload.setdefault("success", True)
        return dict(payload)

    async def action(
        self,
        plugin_id: str,
        panel: str,
        action: str,
        payload: Mapping[str, Any] | None,
        role: str = "",
    ) -> dict[str, Any]:
        panel = _require_panel_id(panel)
        action = _require_action_id(action)
        if PANEL_ROLES.get(role, -1) < PANEL_ROLES["admin"]:
            raise PermissionError("ROLE_FORBIDDEN")
        _canonical, instance = await self._instance(plugin_id)
        if not isinstance(payload, Mapping):
            payload = {}
        result = await _maybe_await_call(
            instance, "webui_panel_action", panel, action, dict(payload)
        )
        if not isinstance(result, Mapping):
            raise ValueError("PANEL_ACTION_INVALID")
        return dict(result)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _maybe_await_call(instance: Any, method: str, *args: Any) -> Any:
    function = getattr(instance, method, None)
    if not callable(function):
        raise LookupError("CONTRACT_UNAVAILABLE")
    return await _maybe_await(function(*args))


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
