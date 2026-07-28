"""凝心溯溪系列的只读运行诊断。"""

from __future__ import annotations

import inspect
from typing import Any

from .health import HEALTH_CONTRACT, HealthChecker


SERIES_MEMBERS: tuple[tuple[str, str], ...] = (
    ("astrbot_plugin_active_learner", "知"),
    ("astrbot_plugin_conversation_flow", "言"),
    ("astrbot_plugin_identity_guardian", "序"),
    ("astrbot_plugin_relationship", "情"),
    ("astrbot_plugin_voice_hub", "声"),
    ("astrbot_plugin_update_manager", "核"),
)


async def diagnose_series(adapter: Any) -> dict[str, object]:
    snapshots = await adapter.snapshot_plugins()
    by_id: dict[str, Any] = {}
    for snapshot in snapshots:
        for identity in (snapshot.name, snapshot.root_dir_name):
            if identity:
                by_id[str(identity)] = snapshot

    rows: list[dict[str, object]] = []
    for plugin_id, label in SERIES_MEMBERS:
        snapshot = by_id.get(plugin_id)
        if snapshot is None:
            rows.append(_row(plugin_id, label, "missing", "PLUGIN_NOT_FOUND"))
            continue
        if not snapshot.loaded:
            rows.append(_row(plugin_id, label, "unhealthy", "PLUGIN_NOT_LOADED", snapshot))
            continue
        if not snapshot.activated:
            rows.append(_row(plugin_id, label, "degraded", "PLUGIN_NOT_ACTIVATED", snapshot))
            continue
        instance = await _instance(adapter, plugin_id)
        if instance is None or getattr(instance, "PLUGIN_HEALTH_CONTRACT", None) is None:
            rows.append(_row(plugin_id, label, "compatible", "L0_ONLY", snapshot))
            continue
        if getattr(instance, "PLUGIN_HEALTH_CONTRACT", None) != HEALTH_CONTRACT:
            rows.append(
                _row(plugin_id, label, "unhealthy", "HEALTH_CONTRACT_INCOMPATIBLE", snapshot)
            )
            continue
        probe = getattr(instance, "plugin_health", None)
        if not callable(probe):
            rows.append(_row(plugin_id, label, "unhealthy", "HEALTH_CONTRACT_INVALID", snapshot))
            continue
        try:
            payload = probe()
            if inspect.isawaitable(payload):
                payload = await payload
        except Exception:
            rows.append(_row(plugin_id, label, "unhealthy", "HEALTH_PROBE_FAILED", snapshot))
            continue
        error = HealthChecker._validate_payload(payload, snapshot.version)
        if error:
            rows.append(_row(plugin_id, label, "unhealthy", error, snapshot))
            continue
        rows.append(_row(plugin_id, label, "ok", "HEALTHY", snapshot))

    healthy_states = {"ok", "compatible"}
    return {
        "status": "ok" if all(row["status"] in healthy_states for row in rows) else "degraded",
        "members": rows,
        "healthy": sum(row["status"] in healthy_states for row in rows),
        "total": len(rows),
    }


async def _instance(adapter: Any, plugin_id: str) -> Any | None:
    getter = getattr(adapter, "get_plugin_instance", None)
    if not callable(getter):
        return None
    try:
        value = getter(plugin_id)
        return await value if inspect.isawaitable(value) else value
    except Exception:
        return None


def _row(
    plugin_id: str,
    label: str,
    status: str,
    reason: str,
    snapshot: Any | None = None,
) -> dict[str, object]:
    return {
        "plugin_id": plugin_id,
        "label": label,
        "status": status,
        "reason": reason,
        "version": str(getattr(snapshot, "version", "") or ""),
    }
