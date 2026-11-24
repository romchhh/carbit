"""Моніторинг AUTO.RIA не має ходити публічним ключем developers.ria.com."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.schemas.schemas import SearchFilters


class MonitorAutoRiaFreshTests(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_window_does_not_use_public_rest_key(self):
        from app.services.search.multi_source import _fetch_source_pool

        filters = SearchFilters(brand="Zeekr", model="001", published_within_hours=24)
        discover = AsyncMock(
            return_value=SimpleNamespace(ids=[], cards={}, market_total=0, error=None)
        )
        hydrate = AsyncMock(return_value=[])
        collect = AsyncMock()

        with (
            patch("app.services.auto_ria.discover.discover_auto_ria", discover),
            patch("app.services.search.pool_cache.hydrate_tagged_auto_ria_ids", hydrate),
            patch("app.services.auto_ria.service.collect_auto_ria_ids", collect),
        ):
            await _fetch_source_pool(
                "auto_ria",
                filters,
                need=40,
                sort_by="published_desc",
            )

        discover.assert_awaited()
        collect.assert_not_awaited()
