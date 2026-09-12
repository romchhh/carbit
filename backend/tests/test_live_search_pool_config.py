"""Regression checks for live-search pool sizing / timeouts."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

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
    def test_auto_ria_hydrate_caps_are_tight(self):
        self.assertLessEqual(multi_source.AUTO_RIA_INFO_HYDRATE_CAP, 40)
        self.assertLessEqual(multi_source.AUTO_RIA_PRICE_SORT_HYDRATE_CAP, 80)
        self.assertLessEqual(multi_source.AR_MODEL_POST_FILTER_CAP, 40)
        self.assertGreaterEqual(multi_source.AUTO_RIA_ID_COLLECT_CAP, 1000)
        self.assertEqual(multi_source._auto_ria_hydrate_cap("newest"), multi_source.AUTO_RIA_INFO_HYDRATE_CAP)
        self.assertEqual(
            multi_source._auto_ria_hydrate_cap("price_asc"),
            multi_source.AUTO_RIA_PRICE_SORT_HYDRATE_CAP,
        )

    def test_split_ar_ids_hydrates_interleaved_window(self):
        used, new = multi_source._split_ar_ids_for_hydrate(
            ["n:1", "10", "n:2", "11", "n:3", "12"],
            4,
        )
        self.assertEqual(used, ["10", "11"])
        self.assertEqual(new, ["1", "2"])

    def test_live_pool_ttl_is_five_to_ten_minutes(self):
        self.assertGreaterEqual(pool_cache.LIVE_POOL_TTL_SECONDS, 300)
        self.assertLessEqual(pool_cache.LIVE_POOL_TTL_SECONDS, 600)

    def test_pool_caps_support_full_catalog(self):
        self.assertGreaterEqual(pool_cache.LIVE_POOL_SIZE, 2000)
        self.assertGreaterEqual(multi_source.SOURCE_POOL_CAP, 2000)
        self.assertEqual(pool_cache.LIVE_POOL_SIZE, multi_source.SOURCE_POOL_CAP)
        self.assertLessEqual(multi_source.OLX_SEARCH_TIMEOUT_SECONDS, 25.0)

    def test_auto_ria_pool_timeout_defined(self):
        self.assertGreater(multi_source.AUTO_RIA_POOL_TIMEOUT_SECONDS, 0)
        self.assertGreater(multi_source.OLX_SEARCH_TIMEOUT_SECONDS, 0)

    def test_merge_multi_source_newest_is_globally_sorted(self):
        batches = [
            (
                "auto_ria",
                PaginatedListings(
                    items=[_listing("a20h", "auto_ria", minutes_ago=20 * 60)],
                    total=1,
                    page=1,
                    per_page=1,
                    pages=1,
                ),
            ),
            (
                "olx",
                PaginatedListings(
                    items=[
                        _listing("o1d", "olx", minutes_ago=24 * 60),
                        _listing("o6d", "olx", minutes_ago=6 * 24 * 60),
                    ],
                    total=2,
                    page=1,
                    per_page=2,
                    pages=1,
                ),
            ),
        ]
        page_items, _, _ = multi_source._merge_multi_source_page(
            batches,
            page=1,
            per_page=3,
            sort_by="newest",
        )
        self.assertEqual([item.id for item in page_items], ["a20h", "o1d", "o6d"])

    def test_fair_merge_newest_prefers_source_blend(self):
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
        page_items, nav_total, _market = multi_source._fair_merge_slice(
            batches,
            page=1,
            per_page=9,
            sort_by="newest",
        )
        self.assertEqual([item.id for item in page_items[:3]], ["o0", "t0", "a0"])
        self.assertGreaterEqual(nav_total, len(page_items))

    def test_sorted_merge_price_stays_global(self):
        batches = [
            (
                "auto_ria",
                PaginatedListings(
                    items=[_listing("a0", "auto_ria", minutes_ago=0)],
                    total=1,
                    page=1,
                    per_page=1,
                    pages=1,
                ),
            ),
            (
                "olx",
                PaginatedListings(
                    items=[_listing("o0", "olx", minutes_ago=0)],
                    total=1,
                    page=1,
                    per_page=1,
                    pages=1,
                ),
            ),
        ]
        page_items, _, _ = multi_source._sorted_merge_slice(
            batches,
            page=1,
            per_page=2,
            sort_by="price_asc",
        )
        self.assertEqual(len(page_items), 2)


class CollapsePoolTotalsTests(unittest.TestCase):
    def test_small_pool_counts_unique_cards_not_raw_slots(self):
        total, pages, offers, dups = pool_cache.collapse_pool_totals(
            slot_total=3,
            unique_count=2,
            page=1,
            per_page=20,
            slot_count=3,
        )
        self.assertEqual(total, 2)
        self.assertEqual(pages, 1)
        self.assertEqual(offers, 3)
        self.assertEqual(dups, 1)

    def test_large_pool_keeps_slot_pagination(self):
        total, pages, offers, dups = pool_cache.collapse_pool_totals(
            slot_total=200,
            unique_count=20,
            page=1,
            per_page=20,
            slot_count=200,
        )
        self.assertEqual(total, 200)
        self.assertEqual(pages, 10)
        self.assertEqual(offers, 200)
        self.assertIsNone(dups)

    def test_no_duplicates(self):
        total, pages, offers, dups = pool_cache.collapse_pool_totals(
            slot_total=2,
            unique_count=2,
            page=1,
            per_page=20,
            slot_count=2,
        )
        self.assertEqual(total, 2)
        self.assertEqual(offers, 2)
        self.assertEqual(dups, 0)
        self.assertEqual(pages, 1)

    def test_remote_html_more_keeps_pagination(self):
        total, pages, offers, dups = pool_cache.collapse_pool_totals(
            slot_total=28,
            unique_count=20,
            page=1,
            per_page=20,
            slot_count=28,
            remote_more=True,
        )
        self.assertEqual(total, 28)
        self.assertEqual(pages, 2)
        self.assertIsNone(dups)

    def test_market_extra_slots_keep_pagination(self):
        total, pages, offers, dups = pool_cache.collapse_pool_totals(
            slot_total=1573,
            unique_count=20,
            page=1,
            per_page=20,
            slot_count=28,
        )
        self.assertEqual(total, 1573)
        self.assertEqual(pages, 79)
        self.assertIsNone(dups)


class HydrateHtmlCardSkipInfoTests(unittest.IsolatedAsyncioTestCase):
    async def test_html_card_skips_auto_ria_info(self):
        html = _listing("auto_ria_40307001", "auto_ria")
        html = html.model_copy(
            update={"source_data": {"html_search": True, "title": "HTML"}}
        )
        slots = [{"s": "r", "i": "40307001", "d": html.model_dump(mode="json")}]
        with patch(
            "app.services.search.pool_cache._batch_hydrate_auto_ria",
            new_callable=AsyncMock,
            return_value={},
        ) as used_mock, patch(
            "app.services.search.pool_cache._batch_hydrate_new_auto_ria",
            new_callable=AsyncMock,
            return_value={},
        ) as new_mock:
            items = await pool_cache._hydrate_page_slots(slots)
        used_mock.assert_awaited_once_with([])
        new_mock.assert_awaited_once_with([])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, "auto_ria_40307001")


class SlicePoolUniquePageTests(unittest.IsolatedAsyncioTestCase):
    async def test_backfills_duplicates_and_sorts_by_published_at(self):
        vin = "WBA8E9C50HK123456"
        slots: list[dict] = []
        for i in range(8):
            item = _listing(f"auto_ria_{i}", "auto_ria", minutes_ago=24 * 60)
            item = item.model_copy(update={"vin": vin})
            slots.append({"s": "o", "d": item.model_dump(mode="json")})
        for i, mins in enumerate((180, 5, 60, 10_000), start=10):
            item = _listing(f"auto_ria_{i}", "auto_ria", minutes_ago=mins)
            slots.append({"s": "o", "d": item.model_dump(mode="json")})

        async def no_db(items):
            from app.services.listings.duplicates import mark_duplicates_in_pool

            return mark_duplicates_in_pool(items)

        with patch.object(pool_cache, "_apply_vin_mirrors_to_page", no_db):
            result = await pool_cache.slice_pool(
                {"slots": slots, "total": len(slots), "market_total": 40},
                page=1,
                per_page=5,
                filters=None,
                sort_by="newest",
            )

        self.assertEqual(len(result.items), 5)
        self.assertEqual(
            [item.id for item in result.items],
            ["auto_ria_11", "auto_ria_12", "auto_ria_10", "auto_ria_0", "auto_ria_13"],
        )


if __name__ == "__main__":
    unittest.main()
