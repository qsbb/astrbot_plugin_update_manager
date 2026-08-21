"""有上限的并发执行helpers，用于批量网络探测。"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Iterable, Sequence, TypeVar

#: 默认并发上限：允许八个可信插件同时检查，同时避免对 GitHub 造成突发压力。
DEFAULT_CHECK_CONCURRENCY = 9

T = TypeVar("T")


def normalize_concurrency(
    value: Any, *, default: int = DEFAULT_CHECK_CONCURRENCY
) -> int:
    """把配置值收敛成 >=1 的整数；非法值回落到默认上限。"""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 1 else default


async def bounded_gather(
    factories: Sequence[Callable[[], Awaitable[T]]] | Iterable[Callable[[], Awaitable[T]]],
    *,
    limit: int = DEFAULT_CHECK_CONCURRENCY,
) -> list[T]:
    """并发执行协程工厂并保持入参顺序，同时最多只有 ``limit`` 个在飞。

    传入的是工厂而不是协程对象：只有拿到信号量后才创建协程，避免大量协程
    在等待期间就被创建出来。
    """
    tasks = list(factories)
    if not tasks:
        return []
    semaphore = asyncio.Semaphore(max(1, limit))

    async def run(factory: Callable[[], Awaitable[T]]) -> T:
        async with semaphore:
            return await factory()

    return list(await asyncio.gather(*(run(factory) for factory in tasks)))
