"""Tests for multi-user search concurrency limits."""

from __future__ import annotations

import asyncio
import unittest

from fastapi import HTTPException

from app.services.search import concurrency as conc


class SearchConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._prev_live = conc._live_sem
        self._prev_olx = conc._olx_sem
        self._prev_auto = conc._auto_ria_sem
        conc._live_sem = asyncio.Semaphore(2)
        conc._olx_sem = asyncio.Semaphore(1)
        conc._auto_ria_sem = asyncio.Semaphore(1)

    async def asyncTearDown(self) -> None:
        conc._live_sem = self._prev_live
        conc._olx_sem = self._prev_olx
        conc._auto_ria_sem = self._prev_auto

    async def test_live_slots_allow_parallel_users(self) -> None:
        started = asyncio.Event()
        release = asyncio.Event()
        in_flight = 0
        max_in_flight = 0

        async def hold() -> None:
            nonlocal in_flight, max_in_flight
            async with conc.acquire_live_search_slot(timeout=2.0):
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
                started.set()
                await release.wait()
                in_flight -= 1

        t1 = asyncio.create_task(hold())
        t2 = asyncio.create_task(hold())
        await asyncio.wait_for(started.wait(), timeout=1.0)
        await asyncio.sleep(0.05)
        self.assertEqual(max_in_flight, 2)
        release.set()
        await asyncio.gather(t1, t2)

    async def test_live_slot_timeout_returns_503(self) -> None:
        gate = asyncio.Event()

        async def hold() -> None:
            async with conc.acquire_live_search_slot(timeout=5.0):
                await gate.wait()

        blockers = [asyncio.create_task(hold()) for _ in range(2)]
        await asyncio.sleep(0.05)

        with self.assertRaises(HTTPException) as ctx:
            async with conc.acquire_live_search_slot(timeout=0.05):
                pass

        self.assertEqual(ctx.exception.status_code, 503)
        gate.set()
        await asyncio.gather(*blockers)

    async def test_identical_searches_coalesce_via_cache(self) -> None:
        from app.schemas.schemas import PaginatedListings
        from app.services.auto_ria.cache import get_or_fetch

        calls = 0

        async def factory() -> PaginatedListings:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.05)
            return PaginatedListings(items=[], total=0, page=1, per_page=20, pages=0)

        key = "coalesce-test-key"

        async def one() -> PaginatedListings:
            return await get_or_fetch(key, factory, ttl_seconds=30)

        results = await asyncio.gather(one(), one(), one())
        self.assertEqual(calls, 1)
        self.assertEqual(len(results), 3)


if __name__ == "__main__":
    unittest.main()
