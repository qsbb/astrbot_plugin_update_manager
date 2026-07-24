from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from astrbot_plugin_auto_updater.core.adapters.astrbot import PluginSnapshot
from astrbot_plugin_auto_updater.core.adapters.storage import (
    AtomicJsonStore,
    FileLeaseLock,
    contained,
    redact,
)
from astrbot_plugin_auto_updater.core.catalog import PluginCatalog
from astrbot_plugin_auto_updater.core.models import (
    Candidate,
    Policy,
    UpdateRule,
    compatible,
    parse_version,
    policy_allows,
)
from astrbot_plugin_auto_updater.core.planner import (
    PlanError,
    PlanStaleError,
    UpdatePlanner,
)
from astrbot_plugin_auto_updater.core.scheduler import (
    RuleConflictError,
    RuleValidationError,
    ScheduleService,
)


class Adapter:
    def __init__(self, snapshots):
        self.snapshots = snapshots

    async def snapshot_plugins(self):
        return tuple(self.snapshots)


def snap(name="demo", version="1.2.3", source=None, reserved=False, activated=True):
    return PluginSnapshot(
        name,
        name,
        name,
        version,
        "https://github.com/acme/demo",
        reserved,
        activated,
        source or {"install_method": "github", "repo": "https://github.com/acme/demo"},
    )


def test_pep440_and_policy():
    assert parse_version("1.10") > parse_version("1.9")
    assert compatible(">=4.16,<5", "4.26.4")
    assert not compatible(">=5", "4.26.4")
    assert policy_allows("1.2.3", "1.2.4", Policy.PATCH)[0]
    assert not policy_allows("1.2.3", "1.3.0", Policy.PATCH)[0]
    assert not policy_allows("1.2.3", "1.2.4rc1", Policy.STABLE)[0]
    assert not policy_allows("0.2.0", "0.2.1", Policy.STABLE)[0]


def test_catalog_explains_security_blocks():
    adapter = Adapter(
        [
            snap(),
            snap("astrbot_plugin_auto_updater"),
            snap("bad", version="wat", source={"install_method": "upload"}),
            snap("reserved", reserved=True),
        ]
    )
    items = asyncio.run(PluginCatalog(adapter).scan())
    by_id = {i.plugin_id: i for i in items}
    assert by_id["demo"].eligible
    assert "SELF_UPDATE_BLOCKED" in by_id["astrbot_plugin_auto_updater"].reasons
    assert {"VERSION_UNPARSEABLE", "SOURCE_REQUIRED"} <= set(by_id["bad"].reasons)
    assert "RESERVED_PLUGIN" in by_id["reserved"].reasons


def test_catalog_rejects_github_lookalike_and_credentials():
    lookalike = snap(
        "lookalike",
        source={
            "install_method": "github",
            "repo": "https://evil.example/github.com/acme/demo",
        },
    )
    credentialed = snap(
        "credentialed",
        source={
            "install_method": "github",
            "repo": "https://token@github.com/acme/demo",
        },
    )
    items = asyncio.run(PluginCatalog(Adapter([lookalike, credentialed])).scan())
    assert all("SOURCE_REQUIRED" in item.reasons for item in items)


def test_plans_are_frozen_and_detect_catalog_change():
    catalog = asyncio.run(PluginCatalog(Adapter([snap()])).scan())
    candidate = Candidate(
        "demo",
        "1.2.3",
        "1.2.4",
        "https://github.com/acme/demo",
        "github",
        astrbot_spec=">=4.16,<5",
    )
    planner = UpdatePlanner(ttl_seconds=60)
    plan = planner.create(
        catalog,
        {"demo": candidate},
        selected=("demo",),
        astrbot_version="4.26.4",
        policy=Policy.PATCH,
        rule_revision=2,
    )
    same = planner.create(
        catalog,
        {"demo": candidate},
        selected=("demo",),
        astrbot_version="4.26.4",
        policy=Policy.PATCH,
        rule_revision=2,
    )
    assert plan.plan_hash != same.plan_hash  # 创建时间属于冻结证据
    planner.validate(plan, catalog, astrbot_version="4.26.4", rule_revision=2)
    changed = asyncio.run(PluginCatalog(Adapter([snap(version="1.2.4")])).scan())
    with pytest.raises(PlanStaleError, match="CATALOG_CHANGED"):
        planner.validate(plan, changed, astrbot_version="4.26.4", rule_revision=2)
    with pytest.raises(PlanStaleError, match="RULE_REVISION"):
        planner.validate(plan, catalog, astrbot_version="4.26.4", rule_revision=3)


def test_planner_rejects_incompatible_and_source_change():
    catalog = asyncio.run(PluginCatalog(Adapter([snap()])).scan())
    planner = UpdatePlanner()
    bad = Candidate("demo", "1.2.3", "1.2.4", "https://github.com/evil/demo", "github")
    with pytest.raises(PlanError, match="SOURCE_CHANGED"):
        planner.create(
            catalog,
            {"demo": bad},
            selected=("demo",),
            astrbot_version="4.26",
            policy=Policy.STABLE,
        )


def test_atomic_store_lock_containment_and_redaction(tmp_path):
    store = AtomicJsonStore(tmp_path / "data")
    store.write("state.json", {"x": 1})
    assert store.read("state.json") == {"x": 1}
    assert contained(store.root / "x", store.root) and not contained(
        store.root.parent / "x", store.root
    )
    assert "secret" not in redact("Authorization: secret").lower()
    first = FileLeaseLock(store.root / "locks" / "x.lock")
    second = FileLeaseLock(store.root / "locks" / "x.lock")
    assert first.acquire() and not second.acquire()
    first.release()
    assert second.acquire()
    second.release()


class Cron:
    def __init__(self):
        self.jobs = []
        self.removed = []

    def add_basic_job(self, **kwargs):
        self.jobs.append(kwargs)

    def remove_job(self, name):
        self.removed.append(name)


def test_rule_cas_timezone_dst_and_duplicate_rebuild(tmp_path):
    store = AtomicJsonStore(tmp_path)
    cron = Cron()
    service = ScheduleService(cron, store, lambda rule: None)
    rule = UpdateRule(
        enabled=True,
        plugin_ids=("demo",),
        local_time="02:30",
        timezone="America/New_York",
        policy="patch",
    )
    saved = service.save(rule, expected_revision=0)
    assert saved.revision == 1
    with pytest.raises(RuleConflictError):
        service.save(rule, expected_revision=0)
    nxt = service.next_run(saved, datetime(2026, 3, 7, 12, tzinfo=timezone.utc))
    assert nxt and nxt.tzinfo is not None
    asyncio.run(service.rebuild())
    asyncio.run(service.rebuild())
    assert len(cron.jobs) == 2 and len(cron.removed) == 2
    with pytest.raises(RuleValidationError):
        service.validate(replace(saved, timezone="Mars/Olympus"))
    asyncio.run(service.close())
