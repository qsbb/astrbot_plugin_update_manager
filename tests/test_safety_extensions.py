from __future__ import annotations

import asyncio
import base64
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


class RegistryResponse:
    def __init__(self, status, payload=None, headers=None):
        self.status = status
        self.payload = payload
        self.headers = headers or {}

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


class RegistryClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


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
    assert candidate.archive_url is None
    assert candidate.evidence == {
        "api": "github_default_branch_metadata",
        "observed_at": candidate.evidence["observed_at"],
        "version_source": "metadata.yaml",
        "matching_tag": False,
    }
    assert [call[0] for call in client.calls[:2]] == [
        "https://api.github.com/repos/acme/demo",
        "https://api.github.com/repos/acme/demo/contents/metadata.yaml?ref=main",
    ]


def test_github_latest_falls_back_to_tag_only_for_release_404(monkeypatch):
    client = RegistryClient(
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
    assert [call[0] for call in client.calls] == [
        "https://api.github.com/repos/acme/demo",
        "https://api.github.com/repos/acme/demo/contents/metadata.yaml?ref=main",
        "https://api.github.com/repos/acme/demo/releases/latest",
        "https://api.github.com/repos/acme/demo/tags?per_page=100",
    ]


@pytest.mark.parametrize("payload", [None, {}, [], ["v1"], [{}]])
def test_github_latest_rejects_invalid_tag_schema(monkeypatch, payload):
    client = RegistryClient(
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
        RegistryResponse(200, {"default_branch": "main"}),
        RegistryResponse(404),
        RegistryResponse(401),
    )
    registry = CandidateRegistry()

    async def get_client():
        return client

    monkeypatch.setattr(registry, "_client", get_client)
    with pytest.raises(RegistryError, match="REGISTRY_HTTP_401"):
        asyncio.run(
            registry.github_latest("demo", "1.0", "https://github.com/acme/demo")
        )
    assert len(client.calls) == 3


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
