"""Інтеграційні тести логіки моніторингу (без зовнішніх API)."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.timezone import KYIV_TZ, now_kyiv
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.search.multi_source import SearchListingsOutcome
from app.services.parser.filter_groups import FilterGroup, group_searches


def _listing_out(listing_id: str = "auto_ria_1") -> ListingOut:
    now = now_kyiv()
    return ListingOut(
        id=listing_id,
        source="auto_ria",
        title="BMW 320",
        brand="BMW",
        model="320",
        year=2019,
        price=15000,
        currency="USD",
        mileage=80000,
        fuel="Бензин",
        transmission="Автомат",
        region="Київ",
        description=None,
        images=[],
        url="https://example.com",
        seller_type="private",
        vin=None,
        source_data=None,
        price_history=[],
        is_duplicate=False,
        published_at=now - timedelta(hours=1),
        found_at=now,
    )


class MonitorParserFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_group_monitor_skips_filter_cache(self):
        from app.services.parser.runner import _process_group

        search = MagicMock()
        search.id = "search-1"
        search.user_id = "user-1"
        search.is_active = True
        search.filters = SearchFilters(brand="BMW", model="320").model_dump()
        search.new_count = 0
        search.total_count = 0

        db = AsyncMock()
        db.get = AsyncMock(return_value=search)
        db.commit = AsyncMock()

        group = group_searches([(search.id, search.filters)])[0]
        item = _listing_out()
        listing = MagicMock()
        listing.id = item.id
        listing.published_at = item.published_at
        listing.found_at = item.found_at

        outcome = SearchListingsOutcome(
            result=PaginatedListings(items=[item], total=1, page=1, per_page=150, pages=1),
            sources=[],
        )
        log: list[str] = []

        with (
            patch("app.services.parser.runner.get_parser_settings", AsyncMock(return_value={
                "notification_max_published_hours": 6,
                "cache_ttl_seconds": 1800,
                "notify_telegram": True,
            })),
            patch("app.services.parser.runner.get_filter_cache", AsyncMock(return_value={
                "fetched_at": now_kyiv().isoformat(),
                "listing_ids": ["auto_ria_old"],
            })),
            patch("app.services.parser.runner.search_listings_outcome", AsyncMock(return_value=outcome)),
            patch("app.services.parser.runner.try_load_pool_listings", AsyncMock(return_value=None)),
            patch("app.services.parser.runner.upsert_listing", AsyncMock(return_value=listing)),
            patch("app.services.parser.runner.set_filter_cache", AsyncMock()),
            patch("app.services.parser.runner.set_monitor_search_ids", return_value=object()),
            patch("app.services.parser.runner.reset_monitor_search_ids"),
            patch("app.services.parser.runner.record_monitor_cycle", AsyncMock()),
            patch("app.services.parser.runner.mark_searches_checked"),
            patch("app.services.parser.runner._deliver_monitor_telegram_for_searches", AsyncMock(return_value=0)),
            patch(
                "app.services.parser.runner._link_listings_to_searches",
                AsyncMock(return_value=(1, 1)),
            ) as link_mock,
        ):
            found, new, sent = await _process_group(
                db,
                group,
                max_listings=150,
                notify=True,
                log=log,
            )

        self.assertEqual(found, 1)
        self.assertEqual(new, 1)
        link_mock.assert_awaited()
        self.assertFalse(any("Кеш" in line and "пропуск API" in line for line in log))

    async def test_acquire_cycle_lock_is_atomic(self):
        from app.services.parser.queue import acquire_cycle_lock, release_cycle_lock

        redis = AsyncMock()
        redis.setnx_ex = AsyncMock(side_effect=[True, False])
        redis.get = AsyncMock(return_value="owner-a")
        redis.delete = AsyncMock()

        with patch("app.services.parser.queue.get_redis", AsyncMock(return_value=redis)):
            first = await acquire_cycle_lock("owner-a")
            second = await acquire_cycle_lock("owner-b")
            await release_cycle_lock("owner-a")

        self.assertTrue(first)
        self.assertFalse(second)
        redis.delete.assert_awaited()


if __name__ == "__main__":
    unittest.main()
