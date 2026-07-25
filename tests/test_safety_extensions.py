from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta

import pytest

from astrbot_plugin_update_manager.core.adapters.registry import (
    CandidateRegistry,
    RegistryError,
)
from astrbot_plugin_update_manager.core.adapters.storage import AtomicJsonStore
from astrbot_plugin_update_manager.core.health import HealthResult
from astrbot_plugin_update_manager.core.models import (
    Candidate,
    CatalogItem,
    PlanItem,
    Policy,
    TxState,
    UpdateRule,
    utc_now,
)
from astrbot_plugin_update_manager.core.planner import PlanError, UpdatePlanner
from astrbot_plugin_update_manager.core.scheduler import RuleValidationError, ScheduleService
from astrbot_plugin_update_manager.core.transaction import PluginTransaction, TransactionError


def catalog_item() -> CatalogItem:
    return CatalogItem(
        "demo",
        "demo",
        "demo",
        "1.2.3",
        "github",
        "https://github.com/acme/demo",
        False,
        False,
        True,
        True,
        (),
        "fingerprint",
    )


def test_plan_hash_is_unique_and_release_age_is_enforced():
    candidate = Candidate(
        "demo",
        "1.2.3",
        "1.2.4",
        "https://github.com/acme/demo",
        "github",
        published_at=(utc_now() - timedelta(hours=48)).isoformat(),
        archive_url="https://api.github.com/repos/acme/demo/zipball/v1.2.4",
    )
    planner = UpdatePlanner()
    kwargs = dict(
        catalog=(catalog_item(),),
        candidates={"demo": candidate},
        selected=("demo",),
        astrbot_version="4.26.4",
        policy=Policy.PATCH,
        rule_revision=1,
        minimum_release_age_hours=24,
    )
    first = planner.create(**kwargs)
    second = planner.create(**kwargs)
    assert first.plan_hash != second.plan_hash
    assert first.items[0].archive_url == candidate.archive_url

    too_new = replace(candidate, published_at=utc_now().isoformat())
    with pytest.raises(PlanError, match="RELEASE_TOO_NEW"):
        planner.create(**{**kwargs, "candidates": {"demo": too_new}})
    with pytest.raises(PlanError, match="RELEASE_AGE_UNKNOWN"):
        planner.create(
            **{**kwargs, "candidates": {"demo": replace(candidate, published_at=None)}}
        )


def test_market_candidate_uses_only_recorded_evidence():
    with pytest.raises(RegistryError, match="UNAVAILABLE"):
        CandidateRegistry.market_candidate("demo", "1.0", "market://demo", {})
    candidate = CandidateRegistry.market_candidate(
        "demo",
        "1.0",
        "market://demo",
        {
            "latest_version": "v1.0.1",
            "download_url": "https://market.example/demo.zip",
            "sha256": "abc",
        },
    )
    assert candidate.target_version == "1.0.1"
    assert candidate.archive_url == "https://market.example/demo.zip"
    assert candidate.digest == "abc"


def test_rule_rejects_unknown_policy_and_failure_mode(tmp_path):
    service = ScheduleService(None, AtomicJsonStore(tmp_path), lambda rule: None)
    with pytest.raises(RuleValidationError, match="INVALID_POLICY"):
        service.validate(UpdateRule(policy="everything"))
    with pytest.raises(RuleValidationError, match="INVALID_FAILURE_POLICY"):
        service.validate(UpdateRule(on_failure="ignore"))


class Adapter:
    def __init__(self, root, *, backup_fails=False):
        self.root = root
        self.version = "1.2.3"
        self.activated = False
        self.backup_fails = backup_fails

    async def update_plugin(self, *args, **kwargs):
        self.version = "1.2.4"
        (self.root / "demo" / "version.txt").write_text("1.2.4")

    async def terminate_plugin(self, plugin_id):
        return None

    async def reload_plugin(self, plugin_id):
        self.version = (self.root / "demo" / "version.txt").read_text()

    async def get_plugin(self, plugin_id):
        return type(
            "Snapshot",
            (),
            {"version": self.version, "activated": self.activated},
        )()


class Health:
    def __init__(self, adapter):
        self.adapter = adapter

    async def check(self, plugin_id, expected_version, *, expected_activated):
        healthy = (
            self.adapter.version == expected_version
            and self.adapter.activated == expected_activated
        )
        return HealthResult(healthy, "HEALTHY" if healthy else "MISMATCH")


def plan_item() -> PlanItem:
    return PlanItem(
        "demo",
        "demo",
        "1.2.3",
        "1.2.4",
        "github",
        "https://github.com/acme/demo",
        False,
        "fingerprint",
    )


def make_transaction(tmp_path):
    root = tmp_path / "plugins"
    (root / "demo").mkdir(parents=True)
    (root / "demo" / "version.txt").write_text("1.2.3")
    store = AtomicJsonStore(tmp_path / "data")
    adapter = Adapter(root)
    tx = PluginTransaction(
        adapter,
        Health(adapter),
        store,
        plugin_root=root,
        backup_root=store.root / "backups",
    )
    return root, store, adapter, tx


def test_prebackup_failure_returns_explicit_failed_terminal(tmp_path, monkeypatch):
    _root, _store, _adapter, tx = make_transaction(tmp_path)

    def fail_backup(item, tx_id):
        raise OSError("disk full")

    monkeypatch.setattr(tx, "backup", fail_backup)
    record = asyncio.run(tx.execute("run", plan_item()))
    assert record["state"] == TxState.FAILED.value
    assert record["finished_at"]


def test_manual_rollback_requires_committed_record_and_version_precondition(tmp_path):
    root, store, adapter, tx = make_transaction(tmp_path)
    committed = asyncio.run(tx.execute("run", plan_item()))
    assert committed["state"] == TxState.COMMITTED.value
    rolled_back = asyncio.run(tx.manual_rollback(committed["tx_id"]))
    assert rolled_back["state"] == TxState.ROLLED_BACK.value
    assert (root / "demo" / "version.txt").read_text() == "1.2.3"

    store.write("tx-bad.json", {"state": "FAILED"})
    with pytest.raises(TransactionError, match="NOT_ROLLBACKABLE"):
        asyncio.run(tx.manual_rollback("bad"))
    adapter.version = "9.9.9"
    with pytest.raises(TransactionError, match="PRECONDITION"):
        asyncio.run(tx.manual_rollback(committed["tx_id"]))


def test_cleanup_keeps_one_restore_point_per_plugin(tmp_path):
    store = AtomicJsonStore(tmp_path / "data")
    plugin_root = tmp_path / "plugins"
    plugin_root.mkdir()
    tx = PluginTransaction(
        Adapter(plugin_root),
        Health(Adapter(plugin_root)),
        store,
        plugin_root=plugin_root,
        backup_root=store.root / "backups",
    )
    for plugin in ("one", "two"):
        path = tx.backup_root / plugin / "only"
        path.mkdir(parents=True)
        (path / "payload").write_bytes(b"x" * 10)
    tx.cleanup(keep_success=1, failed_days=0, capacity_bytes=1)
    assert (tx.backup_root / "one" / "only").exists()
    assert (tx.backup_root / "two" / "only").exists()
