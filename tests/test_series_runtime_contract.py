from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_update_manager.core import diagnostics


class _Adapter:
    def __init__(self) -> None:
        self.instances: dict[str, object] = {}
        self.snapshot_calls = 0

    async def snapshot_plugins(self):
        self.snapshot_calls += 1
        return tuple(
            types.SimpleNamespace(
                name=plugin_id,
                root_dir_name=plugin_id,
                version="1.2.3",
                loaded=True,
                activated=True,
            )
            for plugin_id, _label in diagnostics.SERIES_MEMBERS
        )

    async def get_plugin_instance(self, plugin_id: str):
        return self.instances.get(plugin_id)


def test_runtime_snapshot_normalizes_existing_diagnostics_without_network_or_writes():
    adapter = _Adapter()

    result = asyncio.run(diagnostics.read_series_runtime_snapshot(adapter))

    assert result["contract_name"] == "update_manager.series_runtime"
    assert result["contract_version"] == "1.0"
    assert result["capability"] == "read_runtime_snapshot"
    assert result["status"] == "ok"
    assert result["reason"] == "HEALTHY"
    assert result["healthy"] == result["total"] == len(diagnostics.SERIES_MEMBERS)
    assert adapter.snapshot_calls == 1
    assert all(
        set(member)
        == {
            "plugin_id",
            "label",
            "installed",
            "loaded",
            "activated",
            "version",
            "health_status",
            "reason",
        }
        for member in result["members"]
    )
    assert all(member["installed"] for member in result["members"])
    assert all(member["loaded"] for member in result["members"])
    assert all(member["activated"] for member in result["members"])


def test_incompatible_member_health_contract_is_reported_as_degraded():
    adapter = _Adapter()
    plugin_id = diagnostics.SERIES_MEMBERS[0][0]
    adapter.instances[plugin_id] = types.SimpleNamespace(
        PLUGIN_HEALTH_CONTRACT="plugin.health@2.0",
    )

    result = asyncio.run(diagnostics.read_series_runtime_snapshot(adapter))

    member = result["members"][0]
    assert result["status"] == "degraded"
    assert result["reason"] == "MEMBERS_DEGRADED"
    assert member["health_status"] == "unhealthy"
    assert member["reason"] == "HEALTH_CONTRACT_INCOMPATIBLE"


def test_missing_adapter_is_unavailable_and_non_throwing():
    result = asyncio.run(diagnostics.read_series_runtime_snapshot(None))

    assert result["status"] == "unavailable"
    assert result["reason"] == "ADAPTER_UNAVAILABLE"
    assert result["members"] == []


def test_diagnostic_timeout_is_unavailable_and_non_throwing():
    class SlowAdapter(_Adapter):
        async def snapshot_plugins(self):
            await asyncio.sleep(0.2)
            return ()

    result = asyncio.run(
        diagnostics.read_series_runtime_snapshot(
            SlowAdapter(),
            timeout_seconds=diagnostics.SERIES_RUNTIME_MIN_TIMEOUT_SECONDS,
        )
    )

    assert result["status"] == "unavailable"
    assert result["reason"] == "DIAGNOSTIC_TIMEOUT"


def test_diagnostic_exception_is_error_and_non_throwing():
    class FailingAdapter(_Adapter):
        async def snapshot_plugins(self):
            raise RuntimeError("broken runtime")

    result = asyncio.run(diagnostics.read_series_runtime_snapshot(FailingAdapter()))

    assert result["status"] == "error"
    assert result["reason"] == "DIAGNOSTIC_FAILED"


def test_malformed_internal_report_fails_closed(monkeypatch):
    async def malformed(_adapter):
        return {"status": "ok", "members": [], "healthy": 0, "total": 0}

    monkeypatch.setattr(diagnostics, "diagnose_series", malformed)
    result = asyncio.run(diagnostics.read_series_runtime_snapshot(_Adapter()))

    assert result["status"] == "error"
    assert result["reason"] == "DIAGNOSTIC_INVALID"


def test_semantically_malformed_member_fails_closed(monkeypatch):
    adapter = _Adapter()
    report = asyncio.run(diagnostics.diagnose_series(adapter))
    report["members"][0]["status"] = "missing"

    async def malformed(_adapter):
        return report

    monkeypatch.setattr(diagnostics, "diagnose_series", malformed)
    result = asyncio.run(diagnostics.read_series_runtime_snapshot(adapter))

    assert result["status"] == "error"
    assert result["reason"] == "DIAGNOSTIC_INVALID"


def test_invalid_timeout_request_fails_closed():
    for value in (0, 5.1, "not-a-number", None, True):
        result = asyncio.run(
            diagnostics.read_series_runtime_snapshot(
                _Adapter(),
                timeout_seconds=value,
            )
        )
        assert result["status"] == "error"
        assert result["reason"] == "INVALID_REQUEST"
