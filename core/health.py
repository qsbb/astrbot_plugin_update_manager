"""更新后健康检查。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


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
        return HealthResult(True, "HEALTHY", snapshot.version)
