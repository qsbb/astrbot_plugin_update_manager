from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import replace
from datetime import timedelta

import pytest

from astrbot_plugin_update_manager.core.adapters.registry import (
    DEFAULT_BRANCH_CANDIDATES,
    DEFAULT_CACHE_TTL_SECONDS,
    GITHUB_RAW_HOST,
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


class RegistryResponse:
    def __init__(self, status, payload=None, headers=None, body=None):
        self.status = status
        self.payload = payload
        self.headers = headers or {}
        self.body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")
        return None

    async def json(self, *, content_type=None):
        return self.payload

    async def text(self):
        """raw.githubusercontent.com 返回纯文本 metadata.yaml。"""
        return "" if self.body is None else self.body


def raw_miss(count=len(DEFAULT_BRANCH_CANDIDATES)):
    """raw 域两个候选分支均 404，使 github_latest 回退到 API 路径。"""
    return [RegistryResponse(404) for _ in range(count)]


class RegistryClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)

    @property
    def api_calls(self):
        """忽略 raw 探测，只保留 API 调用，便于断言配额消耗。"""
        return [url for url, _ in self.calls if "api.github.com" in url]


def test_registry_close_releases_real_client_session():
    async def exercise():
        registry = CandidateRegistry()
        session = await registry._client()

        await registry.close()

        assert session.closed is True
        assert registry._session is None
        await registry.close()

    asyncio.run(exercise())


def test_registry_reuses_fresh_ttl_cache_without_network(monkeypatch):
    payload = {"tag_name": "v1.2.3"}
    client = RegistryClient(RegistryResponse(200, payload, {"ETag": '"release-1"'}))
    registry = CandidateRegistry(cache_ttl_seconds=300)

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    first = asyncio.run(registry.fetch_json("https://api.example/releases/latest"))
    second = asyncio.run(registry.fetch_json("https://api.example/releases/latest"))

    assert first is payload
    assert second is payload
    assert len(client.calls) == 1


def test_registry_force_refresh_preserves_etag_and_304_reuses_cache(monkeypatch):
    payload = {"tag_name": "v1.2.3"}
    client = RegistryClient(
        RegistryResponse(200, payload, {"ETag": '"release-1"'}),
        RegistryResponse(304),
    )
    registry = CandidateRegistry(cache_ttl_seconds=300)

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    cached = asyncio.run(registry.fetch_json("https://api.example/releases/latest"))
    refreshed = asyncio.run(
        registry.fetch_json(
            "https://api.example/releases/latest", force_refresh=True
        )
    )

    assert len(client.calls) == 2
    assert client.calls[1][1]["headers"]["If-None-Match"] == '"release-1"'
    assert refreshed is cached
    assert registry._cache["https://api.example/releases/latest"][2] is payload


def test_github_latest_prefers_default_branch_metadata_over_invalid_newer_tags(
    monkeypatch,
):
    metadata = base64.b64encode(
        b"name: active_learner\nversion: 1.2.1.0\n"
    ).decode("ascii")
    client = RegistryClient(
        *raw_miss(),
        RegistryResponse(200, {"default_branch": "main"}),
        RegistryResponse(200, {"encoding": "base64", "content": metadata}),
        RegistryResponse(200, {"tag_name": "v2.6.7.9"}),
        RegistryResponse(
            200,
            [
                {
                    "name": "v2.6.7.8",
                    "zipball_url": "https://api.github.com/repos/acme/demo/zipball/v2.6.7.8",
                    "commit": {"sha": "invalid-tag"},
                }
            ],
        ),
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    candidate = asyncio.run(
        registry.github_latest(
            "active_learner", "1.2.0.0", "https://github.com/acme/demo"
        )
    )

    assert candidate.target_version == "1.2.1.0"
    assert candidate.tag is None
    assert candidate.archive_url == "https://api.github.com/repos/acme/demo/zipball/main"
    assert candidate.default_branch == "main"
    assert candidate.evidence == {
        "api": "github_default_branch_metadata",
        "observed_at": candidate.evidence["observed_at"],
        "version_source": "metadata.yaml",
        "matching_tag": False,
        "quota_free_version_check": False,
    }
    assert client.api_calls[:2] == [
        "https://api.github.com/repos/acme/demo",
        "https://api.github.com/repos/acme/demo/contents/metadata.yaml?ref=main",
    ]


def test_github_latest_uses_master_default_branch_archive_without_matching_tag(
    monkeypatch,
):
    metadata = base64.b64encode(b"name: identity_guardian\nversion: 2.0.0\n").decode(
        "ascii"
    )
    client = RegistryClient(
        *raw_miss(),
        RegistryResponse(200, {"default_branch": "master"}),
        RegistryResponse(200, {"encoding": "base64", "content": metadata}),
        RegistryResponse(404),
        RegistryResponse(200, []),
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    candidate = asyncio.run(
        registry.github_latest(
            "identity_guardian",
            "1.9.0",
            "https://github.com/acme/identity_guardian",
        )
    )

    assert candidate.default_branch == "master"
    assert candidate.archive_url == (
        "https://api.github.com/repos/acme/identity_guardian/zipball/master"
    )
    assert client.api_calls[1].endswith("/contents/metadata.yaml?ref=master")


def test_github_latest_falls_back_to_tag_only_for_release_404(monkeypatch):
    client = RegistryClient(
        *raw_miss(),
        RegistryResponse(200, {"default_branch": "main"}),
        RegistryResponse(404),
        RegistryResponse(404),
        RegistryResponse(
            200,
            [{
                "name": "v1.4.0",
                "zipball_url": "https://api.github.com/repos/acme/demo/zipball/v1.4.0",
                "commit": {"sha": "abc123"},
            }],
            {"ETag": '"tag-1"'},
        ),
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    candidate = asyncio.run(
        registry.github_latest("demo", "1.3.0", "https://github.com/acme/demo")
    )

    assert candidate.target_version == "1.4.0"
    assert candidate.tag == "v1.4.0"
    assert candidate.commit == "abc123"
    assert candidate.archive_url.endswith("/zipball/v1.4.0")
    assert candidate.evidence["api"] == "github_latest_tag"
    assert client.api_calls == [
        "https://api.github.com/repos/acme/demo",
        "https://api.github.com/repos/acme/demo/contents/metadata.yaml?ref=main",
        "https://api.github.com/repos/acme/demo/releases/latest",
        "https://api.github.com/repos/acme/demo/tags?per_page=100",
    ]


@pytest.mark.parametrize("payload", [None, {}, [], ["v1"], [{}]])
def test_github_latest_rejects_invalid_tag_schema(monkeypatch, payload):
    client = RegistryClient(
        *raw_miss(),
        RegistryResponse(200, {"default_branch": "main"}),
        RegistryResponse(404),
        RegistryResponse(404),
        RegistryResponse(200, payload),
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    with pytest.raises(RegistryError, match="GITHUB_TAG_SCHEMA_INVALID"):
        asyncio.run(
            registry.github_latest("demo", "1.0", "https://github.com/acme/demo")
        )


def test_github_latest_does_not_fallback_for_other_errors(monkeypatch):
    client = RegistryClient(
        *raw_miss(),
        RegistryResponse(200, {"default_branch": "main"}),
        RegistryResponse(404),
        RegistryResponse(401),
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    with pytest.raises(RegistryError, match="REGISTRY_HTTP_401") as captured:
        asyncio.run(
            registry.github_latest("demo", "1.0", "https://github.com/acme/demo")
        )
    assert captured.value.to_dict() == {
        "code": "REGISTRY_HTTP_401",
        "context": {
            "repo": "acme/demo",
            "default_branch": "main",
            "http_status": 401,
        },
    }
    assert len(client.api_calls) == 3


def test_github_latest_default_branch_failure_keeps_repo_and_http_status(monkeypatch):
    client = RegistryClient(*raw_miss(), RegistryResponse(401))
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    with pytest.raises(RegistryError) as captured:
        asyncio.run(
            registry.github_latest("demo", "1.0", "https://github.com/acme/demo")
        )
    assert captured.value.to_dict() == {
        "code": "REGISTRY_HTTP_401",
        "context": {"repo": "acme/demo", "http_status": 401},
    }


def test_github_latest_reads_version_from_raw_without_spending_api_quota(monkeypatch):
    """raw 命中默认分支 metadata.yaml 时，不应再请求仓库信息与 contents 接口。"""
    client = RegistryClient(
        RegistryResponse(200, body="name: demo\nversion: 1.4.0\n"),
        RegistryResponse(
            200,
            {
                "tag_name": "v1.4.0",
                "zipball_url": "https://api.github.com/repos/acme/demo/zipball/v1.4.0",
                "published_at": "2024-05-01T00:00:00Z",
            },
        ),
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    candidate = asyncio.run(
        registry.github_latest("demo", "1.3.0", "https://github.com/acme/demo")
    )

    assert candidate.target_version == "1.4.0"
    assert candidate.default_branch == "main"
    assert candidate.evidence["api"] == "github_raw_default_branch_metadata"
    assert candidate.evidence["quota_free_version_check"] is True
    assert client.calls[0][0] == (
        f"https://{GITHUB_RAW_HOST}/acme/demo/main/metadata.yaml"
    )
    # 版本判定阶段零 API 调用，只有补齐 release 证据时才碰 API。
    assert client.api_calls == [
        "https://api.github.com/repos/acme/demo/releases/latest"
    ]


def test_github_latest_probes_master_when_main_branch_is_absent(monkeypatch):
    client = RegistryClient(
        RegistryResponse(404),
        RegistryResponse(200, body="name: demo\nversion: 2.0.0\n"),
        RegistryResponse(404),
        RegistryResponse(200, []),
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    candidate = asyncio.run(
        registry.github_latest("demo", "1.0.0", "https://github.com/acme/demo")
    )

    assert candidate.target_version == "2.0.0"
    assert candidate.default_branch == "master"
    assert [call[0] for call in client.calls[:2]] == [
        f"https://{GITHUB_RAW_HOST}/acme/demo/main/metadata.yaml",
        f"https://{GITHUB_RAW_HOST}/acme/demo/master/metadata.yaml",
    ]


def test_rate_limit_headers_are_recorded_and_reported(monkeypatch):
    reset_epoch = int(time.time()) + 900
    client = RegistryClient(
        RegistryResponse(
            403,
            headers={
                "X-RateLimit-Limit": "60",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_epoch),
                "Retry-After": "120",
            },
        )
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    with pytest.raises(RegistryError) as captured:
        asyncio.run(registry.fetch_json("https://api.github.com/repos/acme/demo"))

    context = captured.value.to_dict()["context"]
    assert captured.value.to_dict()["code"] == "REGISTRY_RATE_LIMITED"
    assert context["rate_limited"] is True
    # retry-after 优先于 reset 推算，UI 才能显示确定的可重试时间。
    assert context["retry_after_seconds"] == pytest.approx(120, abs=2)
    assert context["reset_at"].startswith("20")
    assert context["token_configured"] is False

    status = registry.rate_limit_status()
    assert status["limited"] is True
    assert status["remaining"] == 0
    assert status["limit"] == 60
    assert status["token_configured"] is False


def test_rate_limit_reports_token_configured_when_token_present(monkeypatch):
    client = RegistryClient(
        RegistryResponse(429, headers={"Retry-After": "30"}),
    )
    registry = CandidateRegistry(github_token="ghp_example")

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    with pytest.raises(RegistryError) as captured:
        asyncio.run(registry.fetch_json("https://api.github.com/repos/acme/demo"))

    assert captured.value.to_dict()["context"]["token_configured"] is True
    assert registry.rate_limit_status()["token_configured"] is True


def test_rate_limited_backoff_blocks_further_requests(monkeypatch):
    client = RegistryClient(
        RegistryResponse(
            403, headers={"X-RateLimit-Remaining": "0", "Retry-After": "300"}
        )
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    with pytest.raises(RegistryError, match="REGISTRY_RATE_LIMITED"):
        asyncio.run(registry.fetch_json("https://api.github.com/repos/acme/demo"))
    # 退避窗口内第二次调用必须直接失败，不再发起网络请求耗尽配额。
    with pytest.raises(RegistryError, match="REGISTRY_RATE_LIMITED"):
        asyncio.run(registry.fetch_json("https://api.github.com/repos/acme/other"))

    assert len(client.calls) == 1


def test_rate_limited_prefers_stale_cache_over_failure(monkeypatch):
    payload = {"tag_name": "v1.2.3"}
    url = "https://api.github.com/repos/acme/demo/releases/latest"
    client = RegistryClient(
        RegistryResponse(200, payload),
        RegistryResponse(
            403, headers={"X-RateLimit-Remaining": "0", "Retry-After": "600"}
        ),
    )
    registry = CandidateRegistry(cache_ttl_seconds=0)

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    fresh = asyncio.run(registry.fetch_json(url))
    stale = asyncio.run(registry.fetch_json(url, force_refresh=True))
    # 退避期内继续复用过期缓存，宁可稍旧也不让检查整体失败。
    blocked = asyncio.run(registry.fetch_json(url, force_refresh=True))

    assert fresh is payload
    assert stale is payload
    assert blocked is payload
    assert len(client.calls) == 2


def test_permission_403_without_quota_headers_is_not_treated_as_rate_limit(monkeypatch):
    client = RegistryClient(
        RegistryResponse(403, headers={"X-RateLimit-Remaining": "42"})
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    with pytest.raises(RegistryError, match="REGISTRY_HTTP_403"):
        asyncio.run(registry.fetch_json("https://api.github.com/repos/acme/demo"))

    assert registry.rate_limit_status()["limited"] is False


def test_raw_rate_limit_does_not_block_api_fallback(monkeypatch):
    """raw 域限流不应否定 API：两者配额独立，退避窗口按域名隔离。"""
    metadata = base64.b64encode(b"name: demo\nversion: 3.1.0\n").decode("ascii")
    client = RegistryClient(
        RegistryResponse(429, headers={"Retry-After": "60"}),
        RegistryResponse(200, {"default_branch": "main"}),
        RegistryResponse(200, {"encoding": "base64", "content": metadata}),
        RegistryResponse(404),
        RegistryResponse(200, []),
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    candidate = asyncio.run(
        registry.github_latest("demo", "3.0.0", "https://github.com/acme/demo")
    )

    assert candidate.target_version == "3.1.0"
    assert candidate.evidence["api"] == "github_default_branch_metadata"
    # raw 限流后只探测一次就放弃，剩余分支不再重复请求。
    assert len([url for url, _ in client.calls if GITHUB_RAW_HOST in url]) == 1


def test_default_cache_ttl_is_extended_to_reduce_quota_usage():
    assert CandidateRegistry().cache_ttl == DEFAULT_CACHE_TTL_SECONDS
    assert DEFAULT_CACHE_TTL_SECONDS >= 1800


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
