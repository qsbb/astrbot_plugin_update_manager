from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_update_manager.core.adapters.storage import AtomicJsonStore
from astrbot_plugin_update_manager.core.coordinator import UpdateCoordinator
from astrbot_plugin_update_manager.core.models import TxState
from astrbot_plugin_update_manager.core.transaction import PluginTransaction
from astrbot_plugin_update_manager.pages_api import PagesAPIMixin
from astrbot_plugin_update_manager.series_diagnostics import (
    diagnostic_clear,
    diagnostic_events,
    diagnostic_operation,
)


def test_diagnostic_operation_correlates_timeline_and_redacts_error_text():
    diagnostic_clear()
    operation = diagnostic_operation(
        "candidate",
        "resolve",
        "Candidate resolution",
        details={"requested_count": 3},
    )
    completed = operation.finish(details={"candidate_count": 2})

    assert completed is not None
    assert completed["code"] == "candidate.resolve.completed"
    assert completed["details"]["outcome"] == "success"
    assert completed["details"]["duration_ms"] >= 0
    assert len(completed["details"]["operation_ref"]) == 12
    assert operation.finish() is None

    events = diagnostic_events(limit=10)["events"]
    assert [event["code"] for event in events] == [
        "candidate.resolve.started",
        "candidate.resolve.completed",
    ]
    assert (
        events[0]["details"]["operation_ref"] == events[1]["details"]["operation_ref"]
    )

    failed = diagnostic_operation("page", "save", "Page save")
    failed.fail(RuntimeError("token=do-not-store"), reason="SAVE_FAILED")
    serialized = str(diagnostic_events(limit=10)["events"])
    assert "do-not-store" not in serialized
    assert "RuntimeError" in serialized
    assert "SAVE_FAILED" in serialized


def test_transaction_state_emits_structured_diagnostic(tmp_path):
    events = []

    def emit(code, summary, *, level, details):
        events.append(
            {
                "code": code,
                "summary": summary,
                "level": level,
                "details": details,
            }
        )

    store = AtomicJsonStore(tmp_path / "data")
    plugin_root = tmp_path / "plugins"
    plugin_root.mkdir()
    transaction = PluginTransaction(
        None,
        None,
        store,
        plugin_root=plugin_root,
        backup_root=store.root / "backups",
        diagnostic=emit,
    )
    record = {
        "tx_id": "a" * 32,
        "run_id": "b" * 32,
        "plugin_id": "demo",
        "from_version": "1.0.0",
        "to_version": "1.0.1",
    }

    transaction._record(record, TxState.LOCKED)
    transaction._record(record, TxState.FAILED, error="SAFE_REASON")

    assert [event["code"] for event in events] == [
        "transaction.state",
        "transaction.state",
    ]
    assert events[0]["details"]["tx_ref"] == "a" * 12
    assert events[1]["level"] == "WARNING"
    assert events[1]["details"]["reason"] == "SAFE_REASON"


class _Catalog:
    async def scan(self):
        return ()


class _Planner:
    def validate(self, *args, **kwargs):
        return None


class _Transaction:
    async def execute(self, run_id, item):
        return {"plugin_id": item.plugin_id, "state": TxState.COMMITTED.value}


def test_coordinator_emits_run_timeline_and_recovery(tmp_path):
    events = []

    def emit(code, summary, *, level="INFO", details=None):
        events.append((code, level, details or {}))

    store = AtomicJsonStore(tmp_path)
    coordinator = UpdateCoordinator(
        _Catalog(),
        _Planner(),
        _Transaction(),
        store,
        diagnostic=emit,
    )
    plan = SimpleNamespace(
        plan_hash="plan-hash",
        items=(SimpleNamespace(plugin_id="demo"),),
    )

    result = asyncio.run(
        coordinator.execute(
            plan,
            astrbot_version="4.27.1",
            rule_revision=0,
        )
    )

    assert result["results"][0]["state"] == TxState.COMMITTED.value
    assert [code for code, _level, _details in events[:3]] == [
        "run.started",
        "run.item.completed",
        "run.completed",
    ]
    completed = events[-1][2]
    assert completed["outcome"] == "success"
    assert completed["duration_ms"] >= 0
    assert completed["completed_count"] == 1

    store.write("tx-interrupted.json", {"state": "CORE_UPDATE_RUNNING"})
    assert coordinator.recover_interrupted() == 1
    assert events[-1][0] == "transaction.recovery.completed"
    assert events[-1][2]["recovered_count"] == 1


class _PageHarness(PagesAPIMixin):
    pass


def test_page_diagnostics_classify_status_exception_and_skip_polling():
    harness = _PageHarness()
    diagnostic_clear()

    async def ok():
        return {"success": True}

    async def rejected():
        return {"success": False}, 400

    async def failed():
        raise RuntimeError("token=do-not-store")

    asyncio.run(harness._diagnostic_page_handler("overview", ["GET"], ok)())
    asyncio.run(harness._diagnostic_page_handler("config", ["POST"], rejected)())
    with pytest.raises(RuntimeError):
        asyncio.run(harness._diagnostic_page_handler("update", ["POST"], failed)())

    events = diagnostic_events(limit=20)["events"]
    by_code = {event["code"]: event for event in events}
    assert by_code["page.overview.completed"]["level"] == "DEBUG"
    assert by_code["page.overview.completed"]["details"]["status"] == 200
    assert by_code["page.config.completed"]["level"] == "WARNING"
    assert by_code["page.config.completed"]["details"]["status"] == 400
    assert by_code["page.update.failed"]["level"] == "ERROR"
    assert "do-not-store" not in str(events)

    before = diagnostic_events()["next_seq"]
    polling = harness._diagnostic_page_handler(
        "diagnostics/logs",
        ["POST"],
        ok,
    )
    asyncio.run(polling())
    assert diagnostic_events()["next_seq"] == before
