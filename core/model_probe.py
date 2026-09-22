"""统一模型路由的连通性自检：只调用 AstrBot 官方 ``provider.test()``。

设计要点：
- 只做只读自检，不写配置、不落盘，结果由调用方决定怎么展示。
- 未覆盖官方 ``test()`` 的 provider 一律标 ``unsupported``，避免基类空实现
  被误判成"通过"。
- 任何异常都在这里收敛成 ``failed`` + 脱敏文本，绝不让自检把页面打崩。
"""

from __future__ import annotations

import asyncio
import inspect
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, Iterable, Mapping, Sequence

from .concurrency import bounded_gather

#: 每个职责的超时（秒）。对话类最慢，向量最快。
KIND_TIMEOUTS: dict[str, float] = {
    "conversation": 45.0,
    "fast": 45.0,
    "reasoning": 45.0,
    "vision": 45.0,
    "stt": 45.0,
    "embedding": 20.0,
    "tts": 30.0,
}
DEFAULT_TIMEOUT = 45.0
DEFAULT_CONCURRENCY = 3
ERROR_LIMIT = 200

#: 只有 ``AbstractProvider.test`` 是空实现占位；Provider/STT/TTS/Embedding
#: 等基类的 ``test()`` 都是真实自检，必须算"支持"。
_PLACEHOLDER_TEST_OWNERS = frozenset({"AbstractProvider"})

#: 与其它管理面同款的凭据脱敏规则（只隐藏值，保留错误语义）。
_SECRET_VALUE = re.compile(
    r"(?i)(token|api[_-]?key|secret|password|authorization|cookie|jwt|"
    r"private[_-]?key|ssh[_-]?key|provider[_-]?key|bridge[_-]?key)"
    r"(?:\s*[:=]\s*|\s+)"
    r"(?:bearer\s+)?([^,\s]+)"
)


def safe_error_text(value: Any, *, limit: int = ERROR_LIMIT) -> str:
    """把异常文本压成单行、脱敏、限长。"""
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    text = _SECRET_VALUE.sub(r"\1=<已隐藏>", text)
    if len(text) > limit:
        text = text[: max(1, limit - 1)] + "…"
    return text


def _now() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def provider_test_supported(provider: Any) -> bool:
    """provider 是否实现了官方 ``test()``（而不是继承基类空实现）。"""
    if provider is None:
        return False
    for klass in type(provider).__mro__:
        if "test" in klass.__dict__:
            return klass.__name__ not in _PLACEHOLDER_TEST_OWNERS
    return False


@dataclass(frozen=True, slots=True)
class ResolvedProvider:
    """某个职责最终会用到哪个 provider（解析失败时只有 error）。"""

    provider: Any | None = None
    provider_id: str = ""
    provider_label: str = ""
    source: str = ""
    model: str = ""
    error: str = ""


def _resolved_fields(resolved: ResolvedProvider | None) -> dict[str, str]:
    if resolved is None:
        return {"provider_id": "", "provider_label": "", "source": "", "model": ""}
    return {
        "provider_id": str(resolved.provider_id or ""),
        "provider_label": str(resolved.provider_label or resolved.provider_id or ""),
        "source": str(resolved.source or ""),
        "model": str(resolved.model or ""),
    }


async def probe_kind(
    kind: str,
    resolved: ResolvedProvider | None,
    *,
    timeout: float | None = None,
    runner: Callable[[Any], Awaitable[Any]] | None = None,
) -> dict[str, Any]:
    """自检单个职责，永远返回结果字典，不抛异常。"""
    limit = float(timeout if timeout is not None else KIND_TIMEOUTS.get(kind, DEFAULT_TIMEOUT))
    payload: dict[str, Any] = {
        "kind": kind,
        "tested_at": _now(),
        "timeout_seconds": limit,
        **_resolved_fields(resolved),
    }
    provider = resolved.provider if resolved else None
    if provider is None:
        return {
            **payload,
            "state": "unavailable",
            "latency_ms": 0,
            "error": safe_error_text(
                (resolved.error if resolved else "") or "未解析到可用的模型服务商"
            ),
        }
    if not provider_test_supported(provider):
        return {
            **payload,
            "state": "unsupported",
            "latency_ms": 0,
            "error": "该模型服务商未实现官方自检（provider.test）",
        }

    call = runner or (lambda item: item.test())
    started = time.perf_counter()
    try:
        result = call(provider)
        if inspect.isawaitable(result):
            await asyncio.wait_for(result, timeout=limit)
    except asyncio.TimeoutError:
        return {
            **payload,
            "state": "failed",
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "error": f"自检超时（>{limit:g}s）",
        }
    except Exception as exc:  # noqa: BLE001 - 自检必须吞掉一切异常
        return {
            **payload,
            "state": "failed",
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "error": safe_error_text(exc) or type(exc).__name__,
        }
    return {
        **payload,
        "state": "ok",
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "error": "",
    }


def _timeout_for(kind: str, timeouts: Mapping[str, Any] | None) -> float:
    if timeouts:
        try:
            value = float(timeouts.get(kind, KIND_TIMEOUTS.get(kind, DEFAULT_TIMEOUT)))
        except (TypeError, ValueError):
            value = KIND_TIMEOUTS.get(kind, DEFAULT_TIMEOUT)
        if value > 0:
            return value
    return KIND_TIMEOUTS.get(kind, DEFAULT_TIMEOUT)


async def probe_routes(
    kinds: Iterable[str],
    resolver: Callable[[str], Any],
    *,
    timeouts: Mapping[str, Any] | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict[str, Any]:
    """并发自检多个职责；``resolver`` 可返回 ``ResolvedProvider`` 或 awaitable。

    同一个 provider 实例（例如 fast/reasoning 都继承对话路由）只真调一次，
    其余职责复用结果并标记 ``reused_from``，避免重复计费。
    """
    wanted = [str(kind) for kind in kinds]
    limit = max(1, int(concurrency or DEFAULT_CONCURRENCY))
    started = time.perf_counter()

    resolved: dict[str, ResolvedProvider | None] = {}
    for kind in wanted:
        try:
            value = resolver(kind)
            if inspect.isawaitable(value):
                value = await value
        except Exception as exc:  # noqa: BLE001 - 解析失败也要给出可读结果
            value = ResolvedProvider(error=safe_error_text(exc) or "解析模型服务商失败")
        if value is None or isinstance(value, ResolvedProvider):
            resolved[kind] = value
        else:
            resolved[kind] = ResolvedProvider(provider=value)

    groups: dict[tuple[Any, ...], list[str]] = {}
    for kind in wanted:
        target = resolved.get(kind)
        provider = target.provider if target else None
        key: tuple[Any, ...] = (
            ("provider", id(provider), target.model, target.source)
            if provider is not None
            else ("kind", kind)
        )
        groups.setdefault(key, []).append(kind)

    group_order = list(groups)

    async def run_group(kind_list: list[str]) -> dict[str, dict[str, Any]]:
        primary = kind_list[0]
        timeout = max(_timeout_for(kind, timeouts) for kind in kind_list)
        result = await probe_kind(primary, resolved.get(primary), timeout=timeout)
        entries: dict[str, dict[str, Any]] = {}
        for kind in kind_list:
            entry = dict(result)
            entry["kind"] = kind
            entry["timeout_seconds"] = _timeout_for(kind, timeouts)
            if kind != primary:
                entry["reused_from"] = primary
            entries[kind] = entry
        return entries

    grouped = await bounded_gather(
        [lambda group=groups[key]: run_group(group) for key in group_order], limit=limit
    )
    by_kind: dict[str, dict[str, Any]] = {}
    for chunk in grouped:
        by_kind.update(chunk)
    return {
        "results": [by_kind[kind] for kind in wanted],
        "concurrency": limit,
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "tested_at": _now(),
    }
