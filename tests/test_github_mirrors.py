"""GitHub 镜像加速：前缀拼接、候选解析与"镜像失败回退直连"。"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT.parent))

from astrbot_plugin_update_manager.core.adapters.registry import (  # noqa: E402
    GITHUB_RAW_HOST,
    CandidateRegistry,
    RegistryError,
)
from astrbot_plugin_update_manager.core.mirrors import (  # noqa: E402
    BENCHMARK_PROBE_URL,
    BUILTIN_MIRRORS,
    DEFAULT_BENCHMARK_TIMEOUT_SECONDS,
    apply_mirror,
    available_mirrors,
    normalize_benchmark_timeout,
    normalize_mirror,
    parse_mirror_candidates,
    resolve_mirror,
)


METADATA = "name: demo\nversion: 1.2.3\n"


class Response:
    def __init__(self, status, payload=None, body=None, headers=None):
        self.status = status
        self.payload = payload
        self.body = body
        self.headers = headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def json(self, *, content_type=None):
        return self.payload

    async def text(self):
        return "" if self.body is None else self.body

    async def read(self):
        return b"" if self.body is None else self.body.encode()


class ScriptedClient:
    """按 URL 前缀匹配脚本化响应；未命中即抛连接错误，模拟镜像挂掉。"""

    def __init__(self, script):
        self.script = script
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        for prefix, response in self.script:
            if url.startswith(prefix):
                if isinstance(response, Exception):
                    raise response
                return response
        raise AssertionError(f"unexpected url: {url}")


def bind(registry, client):
    async def get_client():
        return client

    registry._client = get_client
    return client


# ------------------------------------------------------------------ 纯函数


def test_builtin_mirrors_are_the_documented_https_prefixes():
    assert BUILTIN_MIRRORS == (
        "https://edgeone.gh-proxy.com",
        "https://hk.gh-proxy.com",
        "https://gh-proxy.com",
        "https://gh.dpik.top",
    )
    assert all(url.startswith("https://") for url in BUILTIN_MIRRORS)
    assert BENCHMARK_PROBE_URL.startswith("https://raw.githubusercontent.com/")


def test_normalize_mirror_requires_https_and_strips_trailing_slash():
    assert normalize_mirror("https://gh-proxy.com/") == "https://gh-proxy.com"
    assert normalize_mirror("  https://gh.dpik.top//  ") == "https://gh.dpik.top"
    assert normalize_mirror("https://mirror.example.com/gh") == "https://mirror.example.com/gh"
    for bad in (
        "",
        "   ",
        None,
        True,
        "http://gh-proxy.com",
        "ftp://gh-proxy.com",
        "gh-proxy.com",
        "https://",
        "https://user:pass@gh-proxy.com",
        "https://gh-proxy.com/?a=1",
        "https://gh-proxy.com/#frag",
    ):
        assert normalize_mirror(bad) is None, bad


def test_parse_mirror_candidates_splits_dedupes_and_drops_invalid():
    text = (
        "https://a.example.com\n"
        "https://b.example.com, https://a.example.com\n"
        "http://insecure.example.com\n"
        "  \n"
        "not-a-url"
    )
    assert parse_mirror_candidates(text) == (
        "https://a.example.com",
        "https://b.example.com",
    )
    # 中文逗号同样当分隔符，列表输入也走同一条归一化。
    assert parse_mirror_candidates("https://a.example.com，https://b.example.com") == (
        "https://a.example.com",
        "https://b.example.com",
    )
    assert parse_mirror_candidates(["https://a.example.com/", None, 5]) == (
        "https://a.example.com",
    )
    assert parse_mirror_candidates(None) == ()
    assert parse_mirror_candidates("") == ()


def test_available_mirrors_keeps_builtin_first_and_dedupes():
    merged = available_mirrors("https://gh-proxy.com\nhttps://mine.example.com")
    assert merged[: len(BUILTIN_MIRRORS)] == BUILTIN_MIRRORS
    assert merged[-1] == "https://mine.example.com"
    assert len(merged) == len(set(merged))
    assert available_mirrors() == BUILTIN_MIRRORS


def test_apply_mirror_prefixes_full_github_url_only():
    raw = "https://raw.githubusercontent.com/o/r/main/metadata.yaml"
    assert apply_mirror(raw, "https://gh-proxy.com/") == f"https://gh-proxy.com/{raw}"
    api = "https://api.github.com/repos/o/r/zipball/main"
    assert apply_mirror(api, "https://gh.dpik.top") == f"https://gh.dpik.top/{api}"
    # 无镜像、非法镜像、非 GitHub 域名与空 URL 都原样返回。
    assert apply_mirror(raw, None) == raw
    assert apply_mirror(raw, "") == raw
    assert apply_mirror(raw, "http://insecure.example.com") == raw
    assert apply_mirror("https://pypi.org/simple/", "https://gh-proxy.com") == (
        "https://pypi.org/simple/"
    )
    assert apply_mirror("", "https://gh-proxy.com") == ""


def test_resolve_mirror_and_benchmark_timeout_normalization():
    assert resolve_mirror("https://gh-proxy.com/") == "https://gh-proxy.com"
    assert resolve_mirror("") is None
    assert resolve_mirror("nope") is None
    assert normalize_benchmark_timeout(3) == 3.0
    assert normalize_benchmark_timeout("2.5") == 2.5
    for bad in (0, 0.1, -1, None, "abc"):
        assert normalize_benchmark_timeout(bad) == DEFAULT_BENCHMARK_TIMEOUT_SECONDS


# ------------------------------------------------------------------ 注册表


def test_registry_probes_mirror_before_direct_raw():
    registry = CandidateRegistry(cache_ttl_seconds=0, mirror="https://gh-proxy.com/")
    client = bind(
        registry,
        ScriptedClient(
            [("https://gh-proxy.com/", Response(200, body=METADATA))]
        ),
    )
    branch, version, error = asyncio.run(
        registry._raw_metadata_version("o/r", "demo", force_refresh=True)
    )
    assert (branch, version, error) == ("main", "1.2.3", None)
    assert client.urls == [
        "https://gh-proxy.com/"
        f"https://{GITHUB_RAW_HOST}/o/r/main/metadata.yaml"
    ]


def test_mirror_failure_falls_back_to_direct_raw_without_failing_check():
    registry = CandidateRegistry(cache_ttl_seconds=0, mirror="https://gh-proxy.com")
    client = bind(
        registry,
        ScriptedClient(
            [
                ("https://gh-proxy.com/", Response(503)),
                (f"https://{GITHUB_RAW_HOST}/", Response(200, body=METADATA)),
            ]
        ),
    )
    branch, version, error = asyncio.run(
        registry._raw_metadata_version("o/r", "demo", force_refresh=True)
    )
    # 镜像 5xx 不能升级成检查失败，直连必须补上并给出权威版本。
    assert (branch, version, error) == ("main", "1.2.3", None)
    assert len(client.urls) == 2
    assert client.urls[0].startswith("https://gh-proxy.com/")
    assert client.urls[1].startswith(f"https://{GITHUB_RAW_HOST}/")


def test_mirror_404_still_confirmed_by_direct_connection():
    registry = CandidateRegistry(cache_ttl_seconds=0, mirror="https://gh-proxy.com")
    client = bind(
        registry,
        ScriptedClient(
            [
                ("https://gh-proxy.com/", Response(404)),
                (f"https://{GITHUB_RAW_HOST}/", Response(200, body=METADATA)),
            ]
        ),
    )
    branch, version, error = asyncio.run(
        registry._raw_metadata_version("o/r", "demo", force_refresh=True)
    )
    assert (branch, version, error) == ("main", "1.2.3", None)
    assert len(client.urls) == 2


def test_direct_failure_surfaces_registry_error_after_mirror_failure():
    registry = CandidateRegistry(cache_ttl_seconds=0, mirror="https://gh-proxy.com")
    bind(
        registry,
        ScriptedClient(
            [
                ("https://gh-proxy.com/", Response(503)),
                (f"https://{GITHUB_RAW_HOST}/", Response(503)),
            ]
        ),
    )
    branch, version, error = asyncio.run(
        registry._raw_metadata_version("o/r", "demo", force_refresh=True)
    )
    assert (branch, version) == (None, None)
    assert isinstance(error, RegistryError)
    assert error.repo == "o/r"


def test_probe_order_is_direct_only_without_mirror():
    registry = CandidateRegistry()
    url = f"https://{GITHUB_RAW_HOST}/o/r/main/metadata.yaml"
    assert registry._probe_urls(url) == (url,)
    registry.mirror = "https://gh-proxy.com"
    assert registry._probe_urls(url) == (f"https://gh-proxy.com/{url}", url)
    # 非 GitHub 域名即使配了镜像也只探测直连，不会重复请求同一地址。
    assert registry._probe_urls("https://pypi.org/simple/") == ("https://pypi.org/simple/",)


def test_archive_fallback_url_uses_mirror_and_keeps_release_zipball_intact():
    registry = CandidateRegistry(mirror="https://gh.dpik.top/")
    assert registry._archive_fallback_url("o/r", "main") == (
        "https://gh.dpik.top/https://api.github.com/repos/o/r/zipball/main"
    )
    registry.mirror = None
    assert registry._archive_fallback_url("o/r", "feature/x") == (
        "https://api.github.com/repos/o/r/zipball/feature%2Fx"
    )


def test_probe_latency_returns_milliseconds_and_never_raises():
    registry = CandidateRegistry()
    bind(registry, ScriptedClient([("https://", Response(200, body="ok"))]))
    available, latency_ms, error = asyncio.run(
        registry.probe_latency(BENCHMARK_PROBE_URL, timeout_seconds=3)
    )
    assert available is True
    assert isinstance(latency_ms, float) and latency_ms >= 0
    assert error is None

    bind(registry, ScriptedClient([("https://", Response(502))]))
    assert asyncio.run(
        registry.probe_latency(BENCHMARK_PROBE_URL, timeout_seconds=3)
    ) == (False, None, "HTTP_502")

    bind(registry, ScriptedClient([("https://", asyncio.TimeoutError())]))
    assert asyncio.run(
        registry.probe_latency(BENCHMARK_PROBE_URL, timeout_seconds=3)
    ) == (False, None, "TIMEOUT")

    bind(registry, ScriptedClient([("https://", OSError("boom"))]))
    available, latency_ms, error = asyncio.run(
        registry.probe_latency(BENCHMARK_PROBE_URL, timeout_seconds=3)
    )
    assert (available, latency_ms) == (False, None)
    assert error == "OSERROR"


def test_conf_schema_declares_mirror_knobs_with_full_triplet():
    schema = json.loads(
        (PLUGIN_ROOT / "_conf_schema.json").read_text(encoding="utf-8")
    )
    expected = {
        "github_mirror": ("string", ""),
        "github_mirror_candidates": ("string", ""),
        "mirror_benchmark_timeout_seconds": ("float", 5.0),
    }
    for key, (kind, default) in expected.items():
        field = schema[key]
        assert field["type"] == kind
        assert field["default"] == default
        assert field["description"]
