"""更新后健康检查。"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any


HEALTH_CONTRACT = "plugin.health@1.0"


@dataclass(frozen=True, slots=True)
class HealthResult:
    healthy: bool
    reason: str
    observed_version: str | None = None


class HealthChecker:
    def __init__(self, adapter, *, stability_seconds: float = 0.0) -> None:
        self.adapter = adapter
        self.stability_seconds = max(0.0, stability_seconds)

    async def check(
        self, plugin_id: str, expected_version: str, *, expected_activated: bool
    ) -> HealthResult:
        if self.stability_seconds:
            await asyncio.sleep(self.stability_seconds)
        snapshot = await self.adapter.get_plugin(plugin_id)
        if snapshot is None:
            return HealthResult(False, "PLUGIN_NOT_LOADED")
        if snapshot.version != expected_version:
            return HealthResult(False, "VERSION_MISMATCH", snapshot.version)
        if snapshot.activated != expected_activated:
            return HealthResult(False, "ACTIVATION_STATE_CHANGED", snapshot.version)
        instance_getter = getattr(self.adapter, "get_plugin_instance", None)
        if not callable(instance_getter):
            return HealthResult(True, "HEALTHY", snapshot.version)
        try:
            instance = instance_getter(plugin_id)
            if inspect.isawaitable(instance):
                instance = await instance
        except Exception:
            return HealthResult(False, "HEALTH_INSTANCE_LOOKUP_FAILED", snapshot.version)
        if instance is None:
            return HealthResult(True, "HEALTHY", snapshot.version)
        declared = getattr(instance, "PLUGIN_HEALTH_CONTRACT", None)
        if declared is None:
            return HealthResult(True, "HEALTHY", snapshot.version)
        if declared != HEALTH_CONTRACT:
            return HealthResult(False, "HEALTH_CONTRACT_INCOMPATIBLE", snapshot.version)
        probe = getattr(instance, "plugin_health", None)
        if not callable(probe):
            return HealthResult(False, "HEALTH_CONTRACT_INVALID", snapshot.version)
        try:
            payload: Any = probe()
            if inspect.isawaitable(payload):
                payload = await payload
        except Exception:
            return HealthResult(False, "HEALTH_PROBE_FAILED", snapshot.version)
        validation_error = self._validate_payload(payload, expected_version)
        if validation_error:
            return HealthResult(False, validation_error, snapshot.version)
        return HealthResult(True, "HEALTHY", snapshot.version)

    @staticmethod
    def _validate_payload(payload: Any, expected_version: str) -> str:
        if not isinstance(payload, dict) or set(payload) != {
            "status",
            "checks",
            "reasons",
            "version",
        }:
            return "HEALTH_CONTRACT_INVALID"
        status = payload.get("status")
        checks = payload.get("checks")
        reasons = payload.get("reasons")
        version = payload.get("version")
        if status not in {"ok", "degraded", "unhealthy"}:
            return "HEALTH_CONTRACT_INVALID"
        if not isinstance(checks, dict) or not all(
            isinstance(key, str) and isinstance(value, bool)
            for key, value in checks.items()
        ):
            return "HEALTH_CONTRACT_INVALID"
        if not isinstance(reasons, (list, tuple)) or not all(
            isinstance(reason, str) for reason in reasons
        ):
            return "HEALTH_CONTRACT_INVALID"
        if not isinstance(version, str) or version != expected_version:
            return "HEALTH_VERSION_MISMATCH"
        if status != "ok" or not all(checks.values()):
            return "BUSINESS_HEALTH_UNHEALTHY"
        return ""
