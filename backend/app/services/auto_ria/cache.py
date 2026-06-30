from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")

_CACHE: dict[str, tuple[float, Any]] = {}
_INFLIGHT: dict[str, asyncio.Task[Any]] = {}
_LOCK = asyncio.Lock()

DEFAULT_TTL_SECONDS = 120


async def get_or_fetch(
    key: str,
    factory: Callable[[], Awaitable[T]],
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> T:
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached and now < cached[0]:
        return cached[1]

    async with _LOCK:
        cached = _CACHE.get(key)
        if cached and now < cached[0]:
            return cached[1]

        task = _INFLIGHT.get(key)
        if task is None:
            task = asyncio.create_task(factory())
            _INFLIGHT[key] = task
            owner = True
        else:
            owner = False

    try:
        result = await task
        if owner:
            _CACHE[key] = (time.monotonic() + ttl_seconds, result)
        return result
    finally:
        if owner:
            async with _LOCK:
                _INFLIGHT.pop(key, None)
