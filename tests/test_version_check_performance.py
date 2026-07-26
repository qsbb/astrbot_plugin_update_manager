"""并发上限、raw 短超时、默认分支缓存与快速回退的回归测试。"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest
from test_plugin_entry import context, import_main

from astrbot_plugin_update_manager.core.adapters import registry as registry_module
from astrbot_plugin_update_manager.core.adapters.astrbot import PluginSnapshot
from astrbot_plugin_update_manager.core.adapters.registry import (
    DEFAULT_BRANCH_CACHE_TTL_SECONDS,
    DEFAULT_RAW_TIMEOUT_SECONDS,
    GITHUB_RAW_HOST,
    CandidateRegistry,
    RegistryError,
)
from astrbot_plugin_update_manager.core.concurrency import (
    DEFAULT_CHECK_CONCURRENCY,
    bounded_gather,
    normalize_concurrency,
)


def unwrap(response):
    return response[0] if isinstance(response, tuple) else response


class Response:
    def __init__(self, status, payload=None, headers=None, body=None):
        self.status = status
        self.payload = payload
        self.headers = headers or {}
        self.body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def json(self, *, content_type=None):
        return self.payload

    async def text(self):
        return "" if self.body is None else self.body


class RecordingClient:
    """记录每次请求的 URL 与 kwargs，便于断言超时与探测次数。"""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)

    @property
    def urls(self):
        return [url for url, _ in self.calls]

    @property
    def raw_urls(self):
        return [url for url in self.urls if GITHUB_RAW_HOST in url]


class TimeoutClient:
    """raw 域一直超时，用于验证短超时下的快速回退。"""

    def __init__(self, fallback=None):
        self.calls = []
        self.fallback = list(fallback or [])

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if GITHUB_RAW_HOST in url:
            raise asyncio.TimeoutError()
        return self.fallback.pop(0)


def bind(registry, client):
    async def get_client():
        return client

    return get_client


# ----------------------------------------------------------------- 并发 helpers


def test_normalize_concurrency_rejects_invalid_values():
    assert normalize_concurrency(3) == 3
    for value in (0, -1, None, "abc", ""):
        assert normalize_concurrency(value) == DEFAULT_CHECK_CONCURRENCY
    assert normalize_concurrency("4") == 4
    assert normalize_concurrency(0, default=2) == 2


def test_bounded_gather_preserves_order_and_caps_inflight():
    active = 0
    peak = 0

    def factory(value):
        async def run():
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return value

        return run

    results = asyncio.run(
        bounded_gather([factory(index) for index in range(8)], limit=3)
    )

    assert results == list(range(8))
    assert peak <= 3


def test_bounded_gather_handles_empty_and_propagates_failure():
    assert asyncio.run(bounded_gather([])) == []

    async def boom():
        raise RegistryError("REGISTRY_TIMEOUT")

    with pytest.raises(RegistryError, match="REGISTRY_TIMEOUT"):
        asyncio.run(bounded_gather([lambda: boom()], limit=2))


# --------------------------------------------------------------- raw 探测预算


def test_raw_probe_uses_short_independent_timeout_and_single_attempt(monkeypatch):
    """raw 探测必须带独立短超时，且不重试——重试只会累加已知的慢延迟。"""
    client = RecordingClient(
        Response(200, body="name: demo\nversion: 1.4.0\n"),
        Response(404),
        Response(200, []),
    )
    registry = CandidateRegistry(timeout_seconds=15, raw_timeout_seconds=4.0)
    monkeypatch.setattr(registry, "_client", bind(registry, client))

    candidate = asyncio.run(
        registry.github_latest("demo", "1.3.0", "https://github.com/acme/demo")
    )

    assert candidate.target_version == "1.4.0"
    raw_call = next(
        kwargs for url, kwargs in client.calls if GITHUB_RAW_HOST in url
    )
    assert raw_call["timeout"].total == 4.0
    # API 调用不带 per-request timeout，仍沿用会话级全局超时。
    api_call = next(
        kwargs for url, kwargs in client.calls if "api.github.com" in url
    )
    assert "timeout" not in api_call


def test_default_raw_timeout_is_shorter_than_global_network_timeout():
    registry = CandidateRegistry(timeout_seconds=15)
    assert registry.raw_timeout_seconds == DEFAULT_RAW_TIMEOUT_SECONDS
    assert registry.raw_timeout_seconds < registry.timeout.total


def test_raw_timeout_floor_keeps_probe_usable():
    assert CandidateRegistry(raw_timeout_seconds=0).raw_timeout_seconds == 1.0
    assert CandidateRegistry(raw_timeout_seconds=-5).raw_timeout_seconds == 1.0


def test_fetch_text_single_attempt_does_not_retry_timeout(monkeypatch):
    client = TimeoutClient()
    registry = CandidateRegistry()
    monkeypatch.setattr(registry, "_client", bind(registry, client))

    with pytest.raises(RegistryError, match="REGISTRY_TIMEOUT"):
        asyncio.run(
            registry.fetch_text(
                f"https://{GITHUB_RAW_HOST}/acme/demo/main/metadata.yaml",
                timeout_seconds=1.0,
                attempts=1,
            )
        )

    assert len(client.calls) == 1


def test_raw_timeout_falls_back_to_api_and_keeps_readable_error(monkeypatch):
    """raw 超时不能否定 API：必须继续回退，且失败时保留可读错误码。"""
    client = TimeoutClient(fallback=[Response(401)])
    registry = CandidateRegistry()
    monkeypatch.setattr(registry, "_client", bind(registry, client))

    with pytest.raises(RegistryError) as captured:
        asyncio.run(
            registry.github_latest("demo", "1.0", "https://github.com/acme/demo")
        )

    # 超时对第二个分支同样成立，因此只探测一次就放弃 raw，立刻回退 API。
    assert [url for url, _ in client.calls if GITHUB_RAW_HOST in url] == [
        f"https://{GITHUB_RAW_HOST}/acme/demo/main/metadata.yaml"
    ]
    assert captured.value.to_dict() == {
        "code": "REGISTRY_HTTP_401",
        "context": {"repo": "acme/demo", "http_status": 401},
    }


# ------------------------------------------------------------- 默认分支缓存


def test_raw_hit_caches_default_branch_and_skips_second_probe(monkeypatch):
    """首次命中 master 后，后续检查不应再浪费一次注定 404 的 main 探测。"""
    client = RecordingClient(
        Response(404),
        Response(200, body="name: demo\nversion: 2.0.0\n"),
        Response(404),
        Response(200, []),
        Response(200, body="name: demo\nversion: 2.0.1\n"),
        Response(404),
        Response(200, []),
    )
    registry = CandidateRegistry(cache_ttl_seconds=0)
    monkeypatch.setattr(registry, "_client", bind(registry, client))

    first = asyncio.run(
        registry.github_latest("demo", "1.0.0", "https://github.com/acme/demo")
    )
    assert first.default_branch == "master"
    assert registry.remembered_default_branch("acme/demo") == "master"

    second = asyncio.run(
        registry.github_latest("demo", "2.0.0", "https://github.com/acme/demo")
    )

    assert second.target_version == "2.0.1"
    # 第二轮只探测已知的 master，没有再试 main。
    assert client.raw_urls == [
        f"https://{GITHUB_RAW_HOST}/acme/demo/main/metadata.yaml",
        f"https://{GITHUB_RAW_HOST}/acme/demo/master/metadata.yaml",
        f"https://{GITHUB_RAW_HOST}/acme/demo/master/metadata.yaml",
    ]


def test_api_default_branch_is_cached_for_later_raw_probes(monkeypatch):
    """API 查到的默认分支同样要记住，让下一轮 raw 一次命中。"""
    import base64

    metadata = base64.b64encode(b"name: demo\nversion: 3.0.0\n").decode("ascii")
    client = RecordingClient(
        Response(404),
        Response(404),
        Response(200, {"default_branch": "trunk"}),
        Response(200, {"encoding": "base64", "content": metadata}),
        Response(404),
        Response(200, []),
    )
    registry = CandidateRegistry()
    monkeypatch.setattr(registry, "_client", bind(registry, client))

    candidate = asyncio.run(
        registry.github_latest("demo", "2.0.0", "https://github.com/acme/demo")
    )

    assert candidate.default_branch == "trunk"
    assert registry.remembered_default_branch("acme/demo") == "trunk"
    assert registry._branch_probe_order("acme/demo") == ("trunk",)


def test_remembered_default_branch_expires(monkeypatch):
    registry = CandidateRegistry()
    registry._remember_default_branch("acme/demo", "main")
    assert registry.remembered_default_branch("acme/demo") == "main"

    expired = time.monotonic() + DEFAULT_BRANCH_CACHE_TTL_SECONDS + 1
    monkeypatch.setattr(registry_module.time, "monotonic", lambda: expired)

    assert registry.remembered_default_branch("acme/demo") is None
    # 过期条目要被淘汰，回到社区惯例顺序重新探测。
    assert registry._branch_probe_order("acme/demo") == ("main", "master")


def test_unknown_repo_keeps_conventional_probe_order():
    registry = CandidateRegistry()
    assert registry._branch_probe_order("acme/demo") == ("main", "master")


# ------------------------------------------------ 远端版本解析：跨格式兼容


def test_registry_parse_version_handles_v_prefix_and_four_segments():
    """远端 tag/release 名解析同样必须兼容 v 前缀与四段式，且拒绝双重 v。"""
    parse = CandidateRegistry._parse_version
    assert parse("v0.7.4") == parse("0.7.4")
    assert parse("v0.7.4") < parse("0.7.5")
    assert parse("1.2.0.0") == parse("1.2.0")
    assert parse("0.7.9") < parse("0.7.10")
    # removeprefix 只去除一个前导 v；双重 v 解析失败返回 None。
    assert parse("vv1.0") is None
    assert parse(None) is None


def test_metadata_yaml_version_strips_single_v_prefix():
    """metadata.yaml 中残留的 v 前缀版本要归一化为无前缀 PEP 440 版本。"""
    document = "name: demo\nversion: v0.7.5\n"
    assert CandidateRegistry._metadata_yaml_version(document, "demo") == "0.7.5"
    # 三段式无前缀原样通过。
    plain = "name: demo\nversion: 0.7.5\n"
    assert CandidateRegistry._metadata_yaml_version(plain, "demo") == "0.7.5"
    # 双重 v 前缀不是合法 PEP 440，必须报 schema 错误。
    with pytest.raises(RegistryError):
        CandidateRegistry._metadata_yaml_version(
            "name: demo\nversion: vv0.7.5\n", "demo"
        )


# ------------------------------------------------ 页面批量检查：并发与快速回退


def make_plugin(monkeypatch, tmp_path, config=None):
    module = import_main(monkeypatch)
    return module, module.UpdateManagerPlugin(context(tmp_path), config or {})


def test_recommendation_check_respects_configured_concurrency_limit(
    monkeypatch, tmp_path
):
    _, plugin = make_plugin(
        monkeypatch, tmp_path, {"version_check_concurrency": 2}
    )
    active = 0
    peak = 0

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return SimpleNamespace(target_version="9.9.9")

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    payload = unwrap(asyncio.run(plugin._pages_check_recommendations()))

    assert payload["success"] is True
    assert len(payload["items"]) == 6
    assert 1 < peak <= 2


def test_recommendation_check_defaults_to_full_parallel_for_trusted_series(
    monkeypatch, tmp_path
):
    """默认上限要能让六个可信插件同时检查，总耗时不再线性累加。"""
    _, plugin = make_plugin(monkeypatch, tmp_path)
    active = 0
    peak = 0

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1
        return SimpleNamespace(target_version="9.9.9")

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    started = time.monotonic()
    payload = unwrap(asyncio.run(plugin._pages_check_recommendations()))
    elapsed = time.monotonic() - started

    assert payload["success"] is True
    assert len(payload["items"]) == 6
    assert peak == 6
    assert elapsed < 0.02 * 6


def test_invalid_concurrency_config_falls_back_to_default(monkeypatch, tmp_path):
    _, plugin = make_plugin(
        monkeypatch, tmp_path, {"version_check_concurrency": 0}
    )
    assert plugin._version_check_concurrency() == DEFAULT_CHECK_CONCURRENCY

    plugin._config = {"version_check_concurrency": "not-a-number"}
    plugin._config_overrides = {}
    assert plugin._version_check_concurrency() == DEFAULT_CHECK_CONCURRENCY


def test_slow_plugin_check_times_out_without_blocking_the_batch(
    monkeypatch, tmp_path
):
    """单个慢仓库只让自己失败，其余插件仍返回版本，前端不再整体空白。"""
    _, plugin = make_plugin(
        monkeypatch, tmp_path, {"version_check_timeout_seconds": 1}
    )
    monkeypatch.setattr(plugin, "_version_check_timeout", lambda: 0.05)

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        if plugin_id == "astrbot_plugin_voice_hub":
            await asyncio.sleep(5)
        return SimpleNamespace(target_version="9.9.9")

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    started = time.monotonic()
    payload = unwrap(asyncio.run(plugin._pages_check_recommendations()))
    elapsed = time.monotonic() - started

    assert elapsed < 5
    slow = next(
        item
        for item in payload["items"]
        if item["plugin_id"] == "astrbot_plugin_voice_hub"
    )
    assert slow["version_status"] == "check_failed"
    assert slow["error"] == "VERSION_CHECK_TIMEOUT"
    assert slow["error_detail"] == "VERSION_CHECK_TIMEOUT"
    assert slow["error_context"]["repo"] == slow["repo_url"]
    assert slow["latest_version"] == ""
    others = [
        item
        for item in payload["items"]
        if item["plugin_id"] != "astrbot_plugin_voice_hub"
    ]
    assert all(item["latest_version"] == "9.9.9" for item in others)


def test_zero_timeout_disables_the_wall_clock_cap(monkeypatch, tmp_path):
    _, plugin = make_plugin(
        monkeypatch, tmp_path, {"version_check_timeout_seconds": 0}
    )

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        await asyncio.sleep(0.01)
        return SimpleNamespace(target_version="1.2.3")

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    payload = unwrap(asyncio.run(plugin._pages_check_recommendations()))

    assert plugin._version_check_timeout() == 0.0
    assert all(item["latest_version"] == "1.2.3" for item in payload["items"])


def test_invalid_timeout_config_falls_back_to_default(monkeypatch, tmp_path):
    _, plugin = make_plugin(
        monkeypatch, tmp_path, {"version_check_timeout_seconds": "soon"}
    )
    assert plugin._version_check_timeout() == 25.0


def test_apply_page_runtime_config_updates_raw_timeout(monkeypatch, tmp_path):
    _, plugin = make_plugin(monkeypatch, tmp_path)
    plugin._config = {"raw_timeout_seconds": 3.5}
    plugin._config_overrides = {}

    plugin._apply_page_runtime_config()

    assert plugin.registry.raw_timeout_seconds == 3.5


def test_conf_schema_exposes_new_performance_knobs(monkeypatch, tmp_path):
    _, plugin = make_plugin(monkeypatch, tmp_path)
    schema = plugin._schema()
    assert schema["raw_timeout_seconds"]["default"] == DEFAULT_RAW_TIMEOUT_SECONDS
    assert (
        schema["version_check_concurrency"]["default"] == DEFAULT_CHECK_CONCURRENCY
    )
    assert schema["version_check_timeout_seconds"]["default"] == 25


# --------------------------------------------------- 指令路径：候选并发解析


def snapshot(name):
    return PluginSnapshot(
        name,
        name,
        name,
        "1.0.0",
        f"https://github.com/acme/{name}",
        False,
        True,
        True,
        True,
        {"install_method": "github", "repo": f"https://github.com/acme/{name}"},
    )


def test_command_candidates_resolve_concurrently_with_a_cap(monkeypatch, tmp_path):
    """aup plan/dryrun 的候选解析同样并发，不再串行等待每个仓库。"""
    _, plugin = make_plugin(
        monkeypatch, tmp_path, {"version_check_concurrency": 2}
    )
    names = ("alpha", "beta", "gamma", "delta")
    snapshots = tuple(snapshot(name) for name in names)

    async def snapshot_plugins():
        return snapshots

    plugin.adapter.snapshot_plugins = snapshot_plugins
    active = 0
    peak = 0

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return SimpleNamespace(
            plugin_id=plugin_id, target_version="2.0.0", source_url=source_url
        )

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    candidates = asyncio.run(plugin._candidates(names))

    assert sorted(candidates) == sorted(names)
    assert all(
        candidates[name].source_url == f"https://github.com/acme/{name}"
        for name in names
    )
    assert 1 < peak <= 2


def test_command_candidates_keep_duplicate_ids_resolved_once(monkeypatch, tmp_path):
    _, plugin = make_plugin(monkeypatch, tmp_path)

    async def snapshot_plugins():
        return (snapshot("alpha"),)

    plugin.adapter.snapshot_plugins = snapshot_plugins
    calls = []

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        calls.append(plugin_id)
        return SimpleNamespace(target_version="2.0.0", source_url=source_url)

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    candidates = asyncio.run(plugin._candidates(("alpha", "alpha")))

    assert calls == ["alpha"]
    assert set(candidates) == {"alpha"}
