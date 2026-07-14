"""Тести seed baseline для моніторингів."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import ListingOut


def _listing(**kwargs) -> ListingOut:
    base = dict(
        id="auto_ria_1",
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
        published_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
        found_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
    )
    base.update(kwargs)
    return ListingOut(**base)


class SeedBaselineTests(unittest.IsolatedAsyncioTestCase):
    async def test_seed_does_not_increment_new_count(self):
        from app.services.parser.linking import seed_search_baseline

        search = MagicMock()
        search.id = "search-1"
        search.new_count = 0
        search.total_count = 0

        listing = MagicMock()
        listing.id = "auto_ria_1"

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=None)
        db.add = MagicMock()
        db.flush = AsyncMock()

        with patch("app.services.listings.upsert.upsert_listing", AsyncMock(return_value=listing)):
            linked = await seed_search_baseline(db, search, [_listing()])

        self.assertEqual(linked, 1)
        self.assertEqual(search.new_count, 0)
        self.assertEqual(search.total_count, 1)
        added = db.add.call_args[0][0]
        self.assertFalse(added.is_new)


if __name__ == "__main__":
    unittest.main()
