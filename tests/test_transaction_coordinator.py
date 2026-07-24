from __future__ import annotations

import asyncio

import pytest

from astrbot_plugin_auto_updater.core.adapters.storage import AtomicJsonStore
from astrbot_plugin_auto_updater.core.coordinator import (
    PlanAlreadyExecutedError,
    UpdateCoordinator,
)
from astrbot_plugin_auto_updater.core.health import HealthResult
from astrbot_plugin_auto_updater.core.models import (
    CatalogItem,
    PlanItem,
    TxState,
    UpdatePlan,
    stable_hash,
)
from astrbot_plugin_auto_updater.core.planner import UpdatePlanner
from astrbot_plugin_auto_updater.core.transaction import (
    PluginTransaction,
    TransactionError,
)


class Adapter:
    def __init__(self, root, *, fail_health=False):
        self.root = root
        self.version = "1.2.3"
        self.activated = False
        self.fail_health = fail_health
        self.updates = 0

    async def update_plugin(self, *args, **kwargs):
        self.updates += 1
        self.version = "1.2.4"
        (self.root / "demo" / "version.txt").write_text("1.2.4")

    async def terminate_plugin(self, plugin_id):
        pass

    async def reload_plugin(self, plugin_id):
        self.version = (self.root / "demo" / "version.txt").read_text()


class Health:
    def __init__(self, adapter):
        self.adapter = adapter

    async def check(self, plugin_id, expected_version, *, expected_activated):
        if self.adapter.fail_health and expected_version == "1.2.4":
            return HealthResult(False, "BOOM")
        return HealthResult(
            self.adapter.version == expected_version
            and self.adapter.activated == expected_activated,
            "HEALTHY",
            self.adapter.version,
        )


def item():
    return PlanItem(
        "demo",
        "demo",
        "1.2.3",
        "1.2.4",
        "github",
        "https://github.com/a/b",
        False,
        "fp",
    )


def test_transaction_commits_healthy_update(tmp_path):
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
    result = asyncio.run(tx.execute("run", item()))
    assert result["state"] == TxState.COMMITTED.value
    assert adapter.updates == 1


def test_health_failure_rolls_back_and_preserves_disabled(tmp_path):
    root = tmp_path / "plugins"
    (root / "demo").mkdir(parents=True)
    (root / "demo" / "version.txt").write_text("1.2.3")
    store = AtomicJsonStore(tmp_path / "data")
    adapter = Adapter(root, fail_health=True)
    tx = PluginTransaction(
        adapter,
        Health(adapter),
        store,
        plugin_root=root,
        backup_root=store.root / "backups",
    )
    result = asyncio.run(tx.execute("run", item()))
    assert result["state"] == TxState.ROLLED_BACK.value
    assert (root / "demo" / "version.txt").read_text() == "1.2.3"
    assert "共享 Python 依赖" in result["warning"]


def test_backup_rejects_symlink_when_supported(tmp_path):
    root = tmp_path / "plugins"
    (root / "demo").mkdir(parents=True)
    target = tmp_path / "outside"
    target.write_text("x")
    try:
        (root / "demo" / "link").symlink_to(target)
    except OSError:
        pytest.skip("platform cannot create symlink")
    store = AtomicJsonStore(tmp_path / "data")
    adapter = Adapter(root)
    tx = PluginTransaction(
        adapter,
        Health(adapter),
        store,
        plugin_root=root,
        backup_root=store.root / "backups",
    )
    with pytest.raises(TransactionError, match="SYMLINK"):
        tx.backup(item(), "tx")


class Catalog:
    async def scan(self):
        return (
            CatalogItem(
                "demo",
                "demo",
                "demo",
                "1.2.3",
                "github",
                "https://github.com/a/b",
                False,
                False,
                True,
                (),
                "fp",
            ),
        )


class Tx:
    def __init__(self):
        self.calls = 0

    async def execute(self, run_id, plan_item):
        self.calls += 1
        return {"plugin_id": "demo", "state": "COMMITTED"}


def plan():
    return UpdatePlan(
        "p",
        "2026-01-01T00:00:00+00:00",
        "2099-01-01T00:00:00+00:00",
        "4.26",
        stable_hash(["fp"]),
        0,
        "patch",
        (item(),),
        "hash",
    )


def test_coordinator_idempotency_and_cross_process_lock(tmp_path):
    store = AtomicJsonStore(tmp_path)
    tx = Tx()
    coordinator = UpdateCoordinator(Catalog(), UpdatePlanner(), tx, store)
    run = asyncio.run(
        coordinator.execute(plan(), astrbot_version="4.26", rule_revision=0)
    )
    assert run["results"][0]["state"] == "COMMITTED" and tx.calls == 1
    with pytest.raises(PlanAlreadyExecutedError):
        asyncio.run(
            coordinator.execute(plan(), astrbot_version="4.26", rule_revision=0)
        )


def test_interrupted_state_is_persisted(tmp_path):
    store = AtomicJsonStore(tmp_path)
    store.write("tx-x.json", {"state": "CORE_UPDATE_RUNNING"})
    coordinator = UpdateCoordinator(Catalog(), UpdatePlanner(), Tx(), store)
    assert coordinator.recover_interrupted() == 1
    assert store.read("tx-x.json")["state"] == "INTERRUPTED"
