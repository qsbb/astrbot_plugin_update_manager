"""凝心溯溪系列的只读运行诊断。"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

from .health import HEALTH_CONTRACT, HealthChecker
from .trusted import TRUSTED_BY_ID, TRUSTED_SERIES, trusted_plugin_identities


SERIES_MEMBERS: tuple[tuple[str, str], ...] = tuple(
    (item.plugin_id, item.key) for item in TRUSTED_SERIES
)

SERIES_RUNTIME_CONTRACT_NAME = "update_manager.series_runtime"
SERIES_RUNTIME_CONTRACT_VERSION = "1.0"
SERIES_RUNTIME_CONTRACT = (
    f"{SERIES_RUNTIME_CONTRACT_NAME}@{SERIES_RUNTIME_CONTRACT_VERSION}"
)
SERIES_RUNTIME_CAPABILITY = "read_runtime_snapshot"
SERIES_RUNTIME_DEFAULT_TIMEOUT_SECONDS = 2.0
SERIES_RUNTIME_MIN_TIMEOUT_SECONDS = 0.05
SERIES_RUNTIME_MAX_TIMEOUT_SECONDS = 5.0

SERIES_RUNTIME_MEMBER_STATUS_REASONS = {
    "HEALTHY": "ok",
    "L0_ONLY": "compatible",
    "PLUGIN_NOT_ACTIVATED": "degraded",
    "PLUGIN_NOT_FOUND": "missing",
    "PLUGIN_NOT_LOADED": "unhealthy",
    "HEALTH_CONTRACT_INCOMPATIBLE": "unhealthy",
    "HEALTH_CONTRACT_INVALID": "unhealthy",
    "HEALTH_PROBE_FAILED": "unhealthy",
    "HEALTH_VERSION_MISMATCH": "unhealthy",
    "BUSINESS_HEALTH_UNHEALTHY": "unhealthy",
}


async def read_series_runtime_snapshot(
    adapter: Any | None,
    *,
    timeout_seconds: float = SERIES_RUNTIME_DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, object]:
    """Return a bounded, normalized, read-only view of series runtime health."""
    if isinstance(timeout_seconds, bool):
        return _runtime_error("error", "INVALID_REQUEST")
    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError):
        return _runtime_error("error", "INVALID_REQUEST")
    if not SERIES_RUNTIME_MIN_TIMEOUT_SECONDS <= timeout <= SERIES_RUNTIME_MAX_TIMEOUT_SECONDS:
        return _runtime_error("error", "INVALID_REQUEST")
    if adapter is None:
        return _runtime_error("unavailable", "ADAPTER_UNAVAILABLE")

    try:
        report = await asyncio.wait_for(diagnose_series(adapter), timeout=timeout)
    except asyncio.TimeoutError:
        return _runtime_error("unavailable", "DIAGNOSTIC_TIMEOUT")
    except asyncio.CancelledError:
        raise
    except Exception:
        return _runtime_error("error", "DIAGNOSTIC_FAILED")

    normalized = _normalize_runtime_report(report)
    if normalized is None:
        return _runtime_error("error", "DIAGNOSTIC_INVALID")
    return normalized


async def diagnose_series(adapter: Any) -> dict[str, object]:
    snapshots = await adapter.snapshot_plugins()
    by_id: dict[str, Any] = {}
    for snapshot in snapshots:
        for identity in (snapshot.name, snapshot.root_dir_name):
            if identity:
                by_id[str(identity)] = snapshot

    rows: list[dict[str, object]] = []
    for plugin_id, label in SERIES_MEMBERS:
        trusted = TRUSTED_BY_ID[plugin_id]
        snapshot = next(
            (
                by_id.get(identity)
                for identity in trusted_plugin_identities(trusted)
                if by_id.get(identity) is not None
            ),
            None,
        )
        if snapshot is None:
            rows.append(_row(plugin_id, label, "missing", "PLUGIN_NOT_FOUND"))
            continue
        if not snapshot.loaded:
            rows.append(_row(plugin_id, label, "unhealthy", "PLUGIN_NOT_LOADED", snapshot))
            continue
        if not snapshot.activated:
            rows.append(_row(plugin_id, label, "degraded", "PLUGIN_NOT_ACTIVATED", snapshot))
            continue
        instance = await _instance(adapter, *trusted_plugin_identities(trusted))
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


def _runtime_error(status: str, reason: str) -> dict[str, object]:
    return {
        "contract_name": SERIES_RUNTIME_CONTRACT_NAME,
        "contract_version": SERIES_RUNTIME_CONTRACT_VERSION,
        "capability": SERIES_RUNTIME_CAPABILITY,
        "status": status,
        "reason": reason,
        "members": [],
        "healthy": 0,
        "total": 0,
    }


def _normalize_runtime_report(report: Any) -> dict[str, object] | None:
    if not isinstance(report, dict):
        return None
    status = report.get("status")
    members = report.get("members")
    healthy = report.get("healthy")
    total = report.get("total")
    if status not in {"ok", "degraded"} or not isinstance(members, list):
        return None
    if type(healthy) is not int or type(total) is not int:
        return None
    if total != len(SERIES_MEMBERS) or len(members) != total:
        return None

    normalized_members: list[dict[str, object]] = []
    healthy_count = 0
    for row, (expected_id, expected_label) in zip(members, SERIES_MEMBERS, strict=True):
        if not isinstance(row, dict):
            return None
        plugin_id = row.get("plugin_id")
        label = row.get("label")
        member_status = row.get("status")
        reason = row.get("reason")
        version = row.get("version")
        if plugin_id != expected_id or label != expected_label:
            return None
        if not isinstance(reason, str) or not reason:
            return None
        if SERIES_RUNTIME_MEMBER_STATUS_REASONS.get(reason) != member_status:
            return None
        if not isinstance(version, str):
            return None

        installed = member_status != "missing" and reason != "PLUGIN_NOT_FOUND"
        loaded = installed and reason != "PLUGIN_NOT_LOADED"
        activated = loaded and reason != "PLUGIN_NOT_ACTIVATED"
        if member_status in {"ok", "compatible"}:
            healthy_count += 1
        normalized_members.append(
            {
                "plugin_id": plugin_id,
                "label": label,
                "installed": installed,
                "loaded": loaded,
                "activated": activated,
                "version": version,
                "health_status": member_status,
                "reason": reason,
            }
        )

    if healthy != healthy_count:
        return None
    expected_status = "ok" if healthy == total else "degraded"
    if status != expected_status:
        return None
    return {
        "contract_name": SERIES_RUNTIME_CONTRACT_NAME,
        "contract_version": SERIES_RUNTIME_CONTRACT_VERSION,
        "capability": SERIES_RUNTIME_CAPABILITY,
        "status": status,
        "reason": "HEALTHY" if status == "ok" else "MEMBERS_DEGRADED",
        "members": normalized_members,
        "healthy": healthy,
        "total": total,
    }


async def _instance(adapter: Any, *plugin_ids: str) -> Any | None:
    getter = getattr(adapter, "get_plugin_instance", None)
    if not callable(getter):
        return None
    for plugin_id in plugin_ids:
        try:
            value = getter(plugin_id)
            instance = await value if inspect.isawaitable(value) else value
        except Exception:
            continue
        if instance is not None:
            return instance
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
