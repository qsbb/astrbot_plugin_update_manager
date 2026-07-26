from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from astrbot_plugin_update_manager.core.adapters.astrbot import PluginSnapshot
from astrbot_plugin_update_manager.core.adapters.storage import (
    AtomicJsonStore,
    FileLeaseLock,
    contained,
    redact,
)
from astrbot_plugin_update_manager.core.catalog import PluginCatalog
from astrbot_plugin_update_manager.core.models import (
    Candidate,
    Policy,
    UpdateRule,
    compatible,
    parse_version,
    policy_allows,
)
from astrbot_plugin_update_manager.core.planner import (
    PlanError,
    PlanStaleError,
    UpdatePlanner,
)
from astrbot_plugin_update_manager.core.scheduler import (
    RuleConflictError,
    RuleValidationError,
    ScheduleService,
)


class Adapter:
    def __init__(self, snapshots):
        self.snapshots = snapshots

    async def snapshot_plugins(self):
        return tuple(self.snapshots)


def snap(
    name="demo",
    version="1.2.3",
    source=None,
    reserved=False,
    activated=True,
    loaded=True,
):
    return PluginSnapshot(
        name,
        name,
        name,
        version,
        "https://github.com/acme/demo",
        reserved,
        activated,
        loaded,
        True,
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


def test_version_parse_accepts_v_prefix_and_four_segments():
    """系列插件将统一为三段式无 v 前缀；过渡期必须能跨格式正确比较。

    PEP 440 原生接受最多一个前导 v（大小写均可），四段式与三段式按数值
    比较；这里逐条钉住：不允许字符串比较，也不允许双重 v 通过。
    """
    # 带 v 前缀与三段式互相比较（言 v0.6.0 → 0.6.1 类升级）。
    assert parse_version("v0.7.4") == parse_version("0.7.4")
    assert parse_version("v0.7.4") < parse_version("0.7.5")
    # 四段式与三段式（知 1.2.x.x → 1.2.x 类对齐）。
    assert parse_version("1.2.0.0") == parse_version("1.2.0")
    assert parse_version("1.2.3.4") < parse_version("1.2.4")
    assert parse_version("1.2.4") > parse_version("1.2.3.9")
    # 数值比较而非字符串比较：字符串序会把 0.7.10 排在 0.7.9 前面。
    assert parse_version("0.7.9") < parse_version("0.7.10")
    # 只允许一个前导 v；双重前缀与空值必须解析失败。
    assert parse_version("vv1.0") is None
    assert parse_version("") is None
    assert parse_version("not-a-version") is None


def test_policy_allows_across_v_prefix_and_segment_formats():
    """策略判断也必须吃下跨格式版本（v0.7.4 → 0.7.5 判定为补丁升级）。"""
    allowed, reason = policy_allows("v0.7.4", "0.7.5", Policy.CHECK_ONLY)
    assert not allowed and reason == "CHECK_ONLY"  # 0.x 仍按手动/检查策略处理
    assert policy_allows("v1.2.3", "1.2.4", Policy.PATCH)[0]
    assert policy_allows("1.2.0.0", "1.2.1", Policy.PATCH)[0]
    # 同版本跨格式不得误报为可升级。
    assert policy_allows("v1.2.4", "1.2.4", Policy.PATCH) == (False, "NOT_NEWER")
    assert policy_allows("1.2.0.0", "1.2.0", Policy.PATCH) == (False, "NOT_NEWER")


def test_catalog_explains_security_blocks():
    adapter = Adapter(
        [
            snap(),
            snap("astrbot_plugin_update_manager"),
            snap("bad", version="wat", source={"install_method": "upload"}),
            snap("reserved", reserved=True),
            snap("unloaded", loaded=False),
        ]
    )
    items = asyncio.run(PluginCatalog(adapter).scan())
    by_id = {i.plugin_id: i for i in items}
    assert by_id["demo"].eligible
    assert "SELF_UPDATE_BLOCKED" in by_id["astrbot_plugin_update_manager"].reasons
    assert {"VERSION_UNPARSEABLE", "SOURCE_REQUIRED"} <= set(by_id["bad"].reasons)
    assert "RESERVED_PLUGIN" in by_id["reserved"].reasons
    assert by_id["unloaded"].loaded is False
    assert by_id["unloaded"].activated is True  # catalog preserves observed state
    assert by_id["unloaded"].source_kind == "github"
    assert by_id["unloaded"].source_url == "https://github.com/acme/demo"
    assert "PLUGIN_NOT_LOADED" in by_id["unloaded"].reasons
    assert by_id["unloaded"].eligible is False


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
