"""Regression checks for live-search pool sizing / timeouts."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import ListingOut, PaginatedListings
from app.services.search import multi_source, pool_cache


def _listing(listing_id: str, source: str, *, minutes_ago: int = 0) -> ListingOut:
    published = datetime(2026, 7, 17, 12, 0, tzinfo=KYIV_TZ) - timedelta(minutes=minutes_ago)
    return ListingOut(
        id=listing_id,
        source=source,
        title=f"{source} {listing_id}",
        brand="BMW",
        model="X5",
        year=2019,
        price=10_000,
        currency="USD",
        mileage=80_000,
        fuel="Бензин",
        transmission="Автомат",
        region="Київ",
        description=None,
        images=[],
        url=f"https://example.com/{listing_id}",
        seller_type="private",
        vin=None,
        source_data=None,
        price_history=[],
        is_duplicate=False,
        published_at=published,
        found_at=published,
    )


class LiveSearchPoolConfigTests(unittest.TestCase):
    def test_pool_caps_are_bounded(self):
        # Live pool тримає слоти з 3 джерел; OLX/TG всередині ріжуть глибше самі.
        self.assertLessEqual(pool_cache.LIVE_POOL_SIZE, 500)
        self.assertLessEqual(multi_source.SOURCE_POOL_CAP, 500)
        self.assertEqual(pool_cache.LIVE_POOL_SIZE, multi_source.SOURCE_POOL_CAP)
        self.assertLessEqual(multi_source.OLX_SEARCH_TIMEOUT_SECONDS, 25.0)

    def test_auto_ria_pool_timeout_defined(self):
        self.assertGreater(multi_source.AUTO_RIA_POOL_TIMEOUT_SECONDS, 0)
        self.assertGreater(multi_source.OLX_SEARCH_TIMEOUT_SECONDS, 0)

    def test_sorted_merge_newest_global_order(self):
        batches = [
            (
                "auto_ria",
                PaginatedListings(
                    items=[_listing(f"a{i}", "auto_ria", minutes_ago=i) for i in range(30)],
                    total=30,
                    page=1,
                    per_page=30,
                    pages=1,
                ),
            ),
            (
                "olx",
                PaginatedListings(
                    items=[_listing(f"o{i}", "olx", minutes_ago=i + 40) for i in range(20)],
                    total=20,
                    page=1,
                    per_page=20,
                    pages=1,
                ),
            ),
            (
                "telegram",
                PaginatedListings(
                    items=[_listing(f"t{i}", "telegram", minutes_ago=i + 80) for i in range(20)],
                    total=20,
                    page=1,
                    per_page=20,
                    pages=1,
                ),
            ),
        ]
        page_items, nav_total, _market = multi_source._sorted_merge_slice(
            batches,
            page=1,
            per_page=30,
            sort_by="newest",
        )
        self.assertEqual(page_items[0].id, "a0")
        published = [item.published_at for item in page_items]
        self.assertEqual(published, sorted(published, reverse=True))
        self.assertGreaterEqual(nav_total, len(page_items))


if __name__ == "__main__":
    unittest.main()
