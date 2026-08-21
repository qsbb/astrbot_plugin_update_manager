"""Series-wide configuration control plane.

The gateway deliberately knows only the public ``series.control@1.0``
contract.  Plugin configuration ownership remains with each plugin.
"""

from __future__ import annotations

import inspect
import time
from typing import Any, Callable, Mapping

from .adapters.storage import AtomicJsonStore
from .trusted import DIAGNOSTIC_SERIES_ID, TRUSTED_BY_ID, TRUSTED_SERIES

CONTRACT_NAME = "series.control@1.0"
CONTROL_MODES = ("native", "managed")
CONTROL_ROLES = {"viewer": 0, "admin": 1, "owner": 2}
SECRET_KEYS = {"secret", "token", "password", "api_key", "provider_key", "bridge_key"}


def _secret_field(name: str, definition: Mapping[str, Any]) -> bool:
    if bool(definition.get("secret")) or bool(definition.get("write_only")):
        return True
    lowered = name.lower()
    return any(part in lowered for part in SECRET_KEYS)


def _public_schema(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    result: dict[str, Any] = {}
    fields = value.get("fields")
    for key, item in value.items():
        if key == "fields" and isinstance(fields, Mapping):
            safe_fields: dict[str, Any] = {}
            for field, definition in fields.items():
                if not isinstance(definition, Mapping):
                    continue
                safe = dict(definition)
                secret = _secret_field(str(field), safe)
                safe["secret"] = secret
                if secret:
                    safe.pop("default", None)
                    safe.pop("value", None)
                safe_fields[str(field)] = safe
            result[key] = safe_fields
        elif key not in {"value", "effective_value", "native_value"}:
            result[key] = _public_schema(item)
    return result


def _public_snapshot(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in SECRET_KEYS):
                continue
            result[str(key)] = _public_snapshot(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_public_snapshot(item) for item in value]
    return value


class SeriesControlGateway:
    """Fail-closed adapter between the core WebUI and trusted plugins."""

    def __init__(
        self,
        adapter: Any,
        store: AtomicJsonStore,
        *,
        diagnostic: Callable[..., Any] | None = None,
        call_timeout: float = 3.0,
    ) -> None:
        self.adapter = adapter
        self.store = store
        self.diagnostic = diagnostic
        self.call_timeout = max(0.1, float(call_timeout))
        raw = store.read("series-control.json", {})
        self._state = self._normalize_state(raw)

    @staticmethod
    def _normalize_state(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raw = {}
        mode = raw.get("mode") if raw.get("mode") in CONTROL_MODES else "native"
        revision = raw.get("revision", 0)
        try:
            revision = max(0, int(revision))
        except (TypeError, ValueError):
            revision = 0
        members: dict[str, Any] = {}
        if isinstance(raw.get("members"), Mapping):
            for plugin_id, member in raw["members"].items():
                if plugin_id not in TRUSTED_BY_ID or not isinstance(member, Mapping):
                    continue
                policy = member.get("policy", {})
                overrides = member.get("overrides", {})
                members[TRUSTED_BY_ID[plugin_id].plugin_id] = {
                    "policy": dict(policy) if isinstance(policy, Mapping) else {},
                    "overrides": dict(overrides) if isinstance(overrides, Mapping) else {},
                    "revision": max(0, int(member.get("revision", 0) or 0)),
                }
        return {"schema_version": 1, "mode": mode, "revision": revision, "members": members}

    def _save(self) -> None:
        self.store.write("series-control.json", self._state)

    async def _call(self, instance: Any, method: str, *args: Any, **kwargs: Any) -> Any:
        function = getattr(instance, method, None)
        if not callable(function):
            raise LookupError("CONTRACT_UNAVAILABLE")
        value = function(*args, **kwargs)
        if inspect.isawaitable(value):
            return await __import__("asyncio").wait_for(value, self.call_timeout)
        return value

    @staticmethod
    def _canonical(plugin_id: str) -> str:
        trusted = TRUSTED_BY_ID.get(str(plugin_id))
        if trusted is None:
            raise LookupError("PLUGIN_NOT_TRUSTED")
        return trusted.plugin_id

    async def _instance(self, plugin_id: str) -> tuple[str, Any]:
        canonical = self._canonical(plugin_id)
        instance = await self.adapter.get_plugin_instance(canonical)
        if instance is None and canonical != plugin_id:
            instance = await self.adapter.get_plugin_instance(plugin_id)
        if instance is None:
            raise LookupError("PLUGIN_NOT_LOADED")
        contract = await self._call(instance, "series_control_contract")
        if not isinstance(contract, Mapping) or contract.get("name") != CONTRACT_NAME:
            raise LookupError("CONTRACT_UNAVAILABLE")
        if str(contract.get("series_id")) != DIAGNOSTIC_SERIES_ID:
            raise LookupError("CONTRACT_VERSION_UNSUPPORTED")
        if str(contract.get("plugin_id")) not in {canonical, plugin_id}:
            raise LookupError("CONTRACT_VERSION_UNSUPPORTED")
        mode_setter = getattr(instance, "series_control_set_mode", None)
        if callable(mode_setter):
            result = mode_setter(self._state["mode"])
            if inspect.isawaitable(result):
                await result
        return canonical, instance

    def _member(self, plugin_id: str) -> dict[str, Any]:
        return self._state["members"].setdefault(
            plugin_id, {"policy": {}, "overrides": {}, "revision": 0}
        )

    async def overview(self) -> dict[str, Any]:
        rows = []
        for trusted in TRUSTED_SERIES:
            row: dict[str, Any] = {
                "plugin_id": trusted.plugin_id,
                "display_name": trusted.display_name,
                "mode": self._state["mode"],
                "revision": self._member(trusted.plugin_id)["revision"],
                "status": "native",
                "reason": "CONTROL_DISABLED" if self._state["mode"] == "native" else "CONTRACT_UNAVAILABLE",
            }
            try:
                canonical, instance = await self._instance(trusted.plugin_id)
                contract = await self._call(instance, "series_control_contract")
                row.update({"status": "managed" if self._state["mode"] == "managed" else "native", "reason": "OK", "contract": dict(_public_schema(contract)), "plugin_id": canonical})
            except Exception as exc:
                row["reason"] = str(exc) if str(exc) in {"PLUGIN_NOT_LOADED", "CONTRACT_UNAVAILABLE", "CONTRACT_VERSION_UNSUPPORTED"} else "CONTRACT_UNAVAILABLE"
            rows.append(row)
        return {"contract": CONTRACT_NAME, "mode": self._state["mode"], "revision": self._state["revision"], "members": rows}

    async def schema(self, plugin_id: str) -> dict[str, Any]:
        canonical, instance = await self._instance(plugin_id)
        schema = await self._call(instance, "series_control_schema")
        if not isinstance(schema, Mapping):
            raise ValueError("SCHEMA_INVALID")
        return {"success": True, "plugin_id": canonical, "mode": self._state["mode"], "revision": self._member(canonical)["revision"], "schema": _public_schema(schema)}

    async def snapshot(self, plugin_id: str) -> dict[str, Any]:
        canonical, instance = await self._instance(plugin_id)
        snapshot = await self._call(instance, "series_control_snapshot")
        if not isinstance(snapshot, Mapping):
            raise ValueError("SNAPSHOT_INVALID")
        return {"success": True, "plugin_id": canonical, "mode": self._state["mode"], "revision": self._member(canonical)["revision"], "snapshot": _public_snapshot(snapshot)}

    async def validate(self, plugin_id: str, patch: Mapping[str, Any], expected_revision: int) -> dict[str, Any]:
        canonical, instance = await self._instance(plugin_id)
        member = self._member(canonical)
        if int(expected_revision) != int(member["revision"]):
            raise ValueError("REVISION_CONFLICT")
        result = await self._call(instance, "validate_series_control_patch", dict(patch), expected_revision=int(expected_revision))
        if not isinstance(result, Mapping) or result.get("valid") is False:
            raise ValueError("PATCH_INVALID")
        return {"success": True, "plugin_id": canonical, "revision": member["revision"], "validation": _public_snapshot(result)}

    async def apply(self, plugin_id: str, patch: Mapping[str, Any], expected_revision: int, role: str) -> dict[str, Any]:
        if CONTROL_ROLES.get(role, -1) < CONTROL_ROLES["admin"]:
            raise PermissionError("ROLE_REQUIRED")
        canonical, instance = await self._instance(plugin_id)
        member = self._member(canonical)
        if int(expected_revision) != int(member["revision"]):
            raise ValueError("REVISION_CONFLICT")
        await self._call(instance, "validate_series_control_patch", dict(patch), expected_revision=int(expected_revision))
        result = await self._call(instance, "apply_series_control_patch", dict(patch), expected_revision=int(expected_revision))
        if isinstance(result, Mapping) and (
            result.get("success") is False or result.get("status") in {"error", "failed"}
        ):
            raise RuntimeError("APPLY_FAILED_ROLLED_BACK")
        member["overrides"].update(dict(patch))
        member["policy"].update({key: "override" for key in patch})
        member["revision"] += 1
        self._state["revision"] += 1
        self._save()
        return {"success": True, "plugin_id": canonical, "revision": member["revision"], "status": "applied"}

    async def reset(self, plugin_id: str, fields: list[str] | None, role: str) -> dict[str, Any]:
        if CONTROL_ROLES.get(role, -1) < CONTROL_ROLES["admin"]:
            raise PermissionError("ROLE_REQUIRED")
        canonical = self._canonical(plugin_id)
        member = self._member(canonical)
        try:
            _canonical, instance = await self._instance(canonical)
            resetter = getattr(instance, "reset_series_control_override", None)
            if callable(resetter):
                result = resetter(fields, expected_revision=member["revision"])
                if inspect.isawaitable(result):
                    result = await result
                if isinstance(result, Mapping) and (
                    result.get("success") is False
                    or result.get("status") in {"error", "failed"}
                ):
                    raise ValueError(str(result.get("reason") or "RESET_FAILED"))
        except LookupError:
            pass
        selected = set(fields or member["overrides"])
        for field in selected:
            member["overrides"].pop(field, None)
            member["policy"][field] = "inherit"
        member["revision"] += 1
        self._state["revision"] += 1
        self._save()
        return {"success": True, "plugin_id": canonical, "revision": member["revision"], "status": "reset"}

    async def set_mode(self, mode: str, role: str) -> dict[str, Any]:
        if role != "owner":
            raise PermissionError("OWNER_REQUIRED")
        if mode not in CONTROL_MODES:
            raise ValueError("INVALID_MODE")
        self._state["mode"] = mode
        self._state["revision"] += 1
        self._save()
        outcomes = []
        for canonical, member in self._state["members"].items():
            if not member.get("overrides"):
                continue
            try:
                _canonical, instance = await self._instance(canonical)
                mode_setter = getattr(instance, "series_control_set_mode", None)
                if callable(mode_setter):
                    mode_result = mode_setter(mode)
                    if inspect.isawaitable(mode_result):
                        await mode_result
                # The plugin owns its persisted overlay and revision.  A mode
                # switch must only notify it; replaying the patch here would
                # increment the plugin revision without advancing the gateway
                # revision and make the next write fail with a conflict.
                outcomes.append({"plugin_id": canonical, "status": "ok"})
            except Exception as exc:
                outcomes.append({"plugin_id": canonical, "status": "degraded", "reason": str(exc) if str(exc) in {"CONTRACT_UNAVAILABLE", "PLUGIN_NOT_LOADED", "REVISION_CONFLICT"} else "APPLY_FAILED_ROLLED_BACK"})
        return {"success": True, "mode": mode, "revision": self._state["revision"], "outcomes": outcomes}

    async def diagnostics(self, plugin_id: str) -> dict[str, Any]:
        try:
            canonical, instance = await self._instance(plugin_id)
            contract = await self._call(instance, "series_control_contract")
            return {"success": True, "plugin_id": canonical, "status": "ready", "contract": _public_schema(contract), "checked_at": int(time.time())}
        except Exception as exc:
            reason = str(exc) if str(exc) in {"PLUGIN_NOT_TRUSTED", "PLUGIN_NOT_LOADED", "CONTRACT_UNAVAILABLE", "CONTRACT_VERSION_UNSUPPORTED"} else "CONTRACT_UNAVAILABLE"
            return {"success": True, "plugin_id": str(plugin_id), "status": "degraded", "reason": reason}
