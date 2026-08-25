from __future__ import annotations

import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

from app.core.timezone import now_kyiv
from app.models.models import Listing, SearchListing, SearchQuery, Source
from app.schemas.schemas import ListingOut
from app.services.parser.results import _sort_items, get_search_results_from_db, price_drop_counts_for_searches


class MonitorPriceDropSortTests(unittest.TestCase):
    def test_sort_items_by_price_drop_desc(self):
        items = [
            (
                ListingOut(
                    id="a",
                    source="olx",
                    title="A",
                    brand="",
                    model="",
                    year=2020,
                    price=9000,
                    currency="USD",
                    mileage=0,
                    fuel="",
                    transmission="",
                    region="",
                    description=None,
                    images=[],
                    url="",
                    seller_type="private",
                    price_history=[],
                    price_drop_percent=12.0,
                    is_duplicate=False,
                    published_at=now_kyiv(),
                    found_at=now_kyiv(),
                ),
                now_kyiv(),
            ),
            (
                ListingOut(
                    id="b",
                    source="olx",
                    title="B",
                    brand="",
                    model="",
                    year=2020,
                    price=9500,
                    currency="USD",
                    mileage=0,
                    fuel="",
                    transmission="",
                    region="",
                    description=None,
                    images=[],
                    url="",
                    seller_type="private",
                    price_history=[],
                    price_drop_percent=6.0,
                    is_duplicate=False,
                    published_at=now_kyiv(),
                    found_at=now_kyiv(),
                ),
                now_kyiv(),
            ),
        ]
        sorted_items = _sort_items(items, "price_drop_desc")
        self.assertEqual([item.id for item in sorted_items], ["a", "b"])


class MonitorPriceDropFilterTests(unittest.IsolatedAsyncioTestCase):
    async def test_price_drop_counts_for_searches(self):
        search_id = "search-1"
        listing = Listing(
            id="olx_1",
            source=Source.olx,
            title="Test",
            brand="Audi",
            model="A4",
            year=2018,
            price=9000,
            currency="USD",
            mileage=100000,
            fuel="Бензин",
            transmission="Автомат",
            region="Київ",
            url="https://example.test",
            price_history=[
                {
                    "price": 10000,
                    "currency": "USD",
                    "at": (now_kyiv() - timedelta(days=1)).isoformat(),
                }
            ],
            published_at=now_kyiv(),
            found_at=now_kyiv(),
        )
        db = AsyncMock()
        db.execute = AsyncMock(
            return_value=MagicMock(
                all=MagicMock(return_value=[(search_id, listing)]),
            )
        )
        counts = await price_drop_counts_for_searches(db, [search_id])
        self.assertEqual(counts[search_id], 1)

    async def test_get_search_results_price_drops_only(self):
        search = SearchQuery(
            id="search-1",
            user_id="user-1",
            name="Test",
            filters={"brand": "Audi"},
        )
        listing_drop = Listing(
            id="olx_1",
            source=Source.olx,
            title="Drop",
            brand="Audi",
            model="A4",
            year=2018,
            price=9000,
            currency="USD",
            mileage=100000,
            fuel="Бензин",
            transmission="Автомат",
            region="Київ",
            url="https://example.test/1",
            price_history=[
                {
                    "price": 10000,
                    "currency": "USD",
                    "at": (now_kyiv() - timedelta(days=1)).isoformat(),
                }
            ],
            published_at=now_kyiv(),
            found_at=now_kyiv(),
        )
        listing_plain = Listing(
            id="olx_2",
            source=Source.olx,
            title="Plain",
            brand="Audi",
            model="A4",
            year=2018,
            price=10000,
            currency="USD",
            mileage=100000,
            fuel="Бензин",
            transmission="Автомат",
            region="Київ",
            url="https://example.test/2",
            price_history=[],
            published_at=now_kyiv(),
            found_at=now_kyiv(),
        )
        db = AsyncMock()
        db.execute = AsyncMock(
            return_value=MagicMock(
                all=MagicMock(
                    return_value=[
                        (listing_drop, SearchListing(search_id=search.id, listing_id=listing_drop.id)),
                        (listing_plain, SearchListing(search_id=search.id, listing_id=listing_plain.id)),
                    ]
                ),
            )
        )

        async def collapse(db_arg, items):
            return items

        from app.services.listings import duplicates

        originals = duplicates.collapse_listings_with_db_mirrors
        duplicates.collapse_listings_with_db_mirrors = collapse
        try:
            result = await get_search_results_from_db(
                db,
                search,
                page=1,
                per_page=20,
                sort_by="price_drop_desc",
                price_drops_only=True,
            )
        finally:
            duplicates.collapse_listings_with_db_mirrors = originals

        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].id, "olx_1")
        self.assertGreaterEqual(result.items[0].price_drop_percent or 0, 5)


if __name__ == "__main__":
    unittest.main()
