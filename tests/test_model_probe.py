from __future__ import annotations

import asyncio
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core.model_probe import (
    DEFAULT_CONCURRENCY,
    KIND_TIMEOUTS,
    ResolvedProvider,
    probe_kind,
    probe_routes,
    provider_test_supported,
    safe_error_text,
)


class AbstractProvider:
    """模拟 AstrBot 的占位基类：test() 是空实现。"""

    async def test(self) -> None:  # pragma: no cover - 只是占位
        ...


class ChatProvider(AbstractProvider):
    """模拟真实 provider：test() 会做一次极小真实调用。"""

    def __init__(self, *, delay: float = 0.0, error: Exception | None = None) -> None:
        self.delay = delay
        self.error = error
        self.calls = 0

    async def test(self, timeout: float = 45.0) -> None:
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error


class BareProvider(AbstractProvider):
    """继承占位基类但没覆写：必须判为 unsupported。"""


def test_provider_test_supported_detects_placeholder_base():
    assert provider_test_supported(ChatProvider()) is True
    assert provider_test_supported(BareProvider()) is False
    assert provider_test_supported(None) is False


def test_safe_error_text_masks_secrets_and_trims_newlines():
    masked = safe_error_text("call failed api_key=sk-secret123\nsecond line")
    assert "sk-secret123" not in masked
    assert "<已隐藏>" in masked
    assert "\n" not in masked
    assert len(safe_error_text("x" * 500)) == 200


def test_probe_kind_ok_and_failed_and_unavailable_and_unsupported():
    async def run():
        ok = await probe_kind("fast", ResolvedProvider(provider=ChatProvider(), provider_id="p1"))
        failed = await probe_kind(
            "fast",
            ResolvedProvider(provider=ChatProvider(error=RuntimeError("401 token=abc")), provider_id="p2"),
        )
        unavailable = await probe_kind("tts", None)
        unsupported = await probe_kind(
            "embedding", ResolvedProvider(provider=BareProvider(), provider_id="p3")
        )
        return ok, failed, unavailable, unsupported

    ok, failed, unavailable, unsupported = asyncio.run(run())
    assert ok["state"] == "ok" and ok["provider_id"] == "p1" and ok["error"] == ""
    assert failed["state"] == "failed"
    assert "abc" not in failed["error"] and "<已隐藏>" in failed["error"]
    assert unavailable["state"] == "unavailable" and unavailable["provider_id"] == ""
    assert unsupported["state"] == "unsupported"
    assert all(item["latency_ms"] >= 0 for item in (ok, failed, unavailable, unsupported))


def test_probe_kind_timeout_is_reported_as_failed():
    async def run():
        return await probe_kind(
            "fast",
            ResolvedProvider(provider=ChatProvider(delay=0.2), provider_id="slow"),
            timeout=0.05,
        )

    result = asyncio.run(run())
    assert result["state"] == "failed"
    assert "超时" in result["error"]
    assert result["timeout_seconds"] == 0.05


def test_probe_routes_covers_all_kinds_and_respects_concurrency():
    seen: list[str] = []
    active = 0
    peak = 0

    async def resolver(kind: str) -> ResolvedProvider:
        nonlocal active, peak
        seen.append(kind)
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return ResolvedProvider(provider=ChatProvider(), provider_id=f"p-{kind}")

    kinds = ["conversation", "fast", "reasoning", "embedding", "vision", "stt", "tts"]
    payload = asyncio.run(probe_routes(kinds, resolver, concurrency=2))

    assert [item["kind"] for item in payload["results"]] == kinds
    assert all(item["state"] == "ok" for item in payload["results"])
    assert payload["concurrency"] == 2
    assert peak <= 2
    assert seen == kinds
    assert payload["duration_ms"] >= 0
    assert payload["tested_at"]


def test_probe_routes_uses_per_kind_timeouts_and_survives_resolver_errors():
    def resolver(kind: str):
        if kind == "tts":
            raise RuntimeError("resolver blew up")
        return ChatProvider()

    payload = asyncio.run(probe_routes(["fast", "tts"], resolver))
    by_kind = {item["kind"]: item for item in payload["results"]}
    assert by_kind["fast"]["state"] == "ok"
    assert by_kind["tts"]["state"] == "unavailable"
    assert "resolver blew up" in by_kind["tts"]["error"]
    assert by_kind["fast"]["timeout_seconds"] == KIND_TIMEOUTS["fast"]
    assert by_kind["tts"]["timeout_seconds"] == KIND_TIMEOUTS["tts"]
    assert payload["concurrency"] == DEFAULT_CONCURRENCY


def test_probe_routes_deduplicates_shared_provider_instances():
    """fast/reasoning 继承对话路由时，同一个 provider 只真调一次。"""
    shared = ChatProvider()

    payload = asyncio.run(
        probe_routes(
            ["conversation", "fast", "reasoning"],
            lambda kind: ResolvedProvider(provider=shared, provider_id="p-shared", source="astrbot"),
            concurrency=3,
        )
    )
    assert shared.calls == 1
    by_kind = {item["kind"]: item for item in payload["results"]}
    assert by_kind["conversation"]["state"] == "ok"
    assert "reused_from" not in by_kind["conversation"]
    assert by_kind["fast"]["reused_from"] == "conversation"
    assert by_kind["reasoning"]["reused_from"] == "conversation"


def test_probe_routes_accepts_plain_provider_and_sync_runner():
    calls: list[str] = []

    async def runner(provider) -> None:
        calls.append("called")

    payload = asyncio.run(
        probe_routes(["fast"], lambda kind: ChatProvider(), concurrency=1)
    )
    assert payload["results"][0]["state"] == "ok"

    async def run_sync_runner():
        return await probe_kind("fast", ResolvedProvider(provider=ChatProvider()), runner=runner)

    result = asyncio.run(run_sync_runner())
    assert result["state"] == "ok"
    assert calls == ["called"]
