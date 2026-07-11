"""Process-wide limits so many users can search concurrently without melting upstreams.

One uvicorn worker already multiplexes requests on the asyncio event loop.
These semaphores add backpressure: extra requests wait (or get 503) instead of
hammering AUTO.RIA / OLX and starving everyone.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import HTTPException

# Live multi-source searches in flight (each may fan out to 3 sources)
LIVE_SEARCH_LIMIT = 8
# Concurrent OLX scrapes (slow + polite delays — keep low)
OLX_SCRAPE_LIMIT = 2
# Concurrent AUTO.RIA search pipelines (API key shared)
AUTO_RIA_SEARCH_LIMIT = 6

# How long a user waits for a free slot before we reject
LIVE_SEARCH_WAIT_SECONDS = 45.0
OLX_WAIT_SECONDS = 50.0
AUTO_RIA_WAIT_SECONDS = 30.0

_live_sem = asyncio.Semaphore(LIVE_SEARCH_LIMIT)
_olx_sem = asyncio.Semaphore(OLX_SCRAPE_LIMIT)
_auto_ria_sem = asyncio.Semaphore(AUTO_RIA_SEARCH_LIMIT)


@asynccontextmanager
async def acquire_live_search_slot(
    *,
    timeout: float = LIVE_SEARCH_WAIT_SECONDS,
) -> AsyncIterator[None]:
    try:
        await asyncio.wait_for(_live_sem.acquire(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            503,
            "Занадто багато одночасних пошуків. Спробуйте ще раз за кілька секунд.",
        ) from exc
    try:
        yield
    finally:
        _live_sem.release()


@asynccontextmanager
async def acquire_olx_slot(
    *,
    timeout: float = OLX_WAIT_SECONDS,
) -> AsyncIterator[None]:
    try:
        await asyncio.wait_for(_olx_sem.acquire(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise TimeoutError("OLX: черга пошуку переповнена") from exc
    try:
        yield
    finally:
        _olx_sem.release()


@asynccontextmanager
async def acquire_auto_ria_slot(
    *,
    timeout: float = AUTO_RIA_WAIT_SECONDS,
) -> AsyncIterator[None]:
    try:
        await asyncio.wait_for(_auto_ria_sem.acquire(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise TimeoutError("AUTO.RIA: черга пошуку переповнена") from exc
    try:
        yield
    finally:
        _auto_ria_sem.release()
