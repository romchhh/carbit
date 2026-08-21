from __future__ import annotations

import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.timezone import now_kyiv
from app.models.models import NotificationType
from app.services.listings.price_drop import (
    MIN_SIGNIFICANT_PRICE_DROP_PERCENT,
    compute_drop_percent,
    extract_recent_price_drop,
    is_significant_price_drop,
)
from app.services.notifications.listing_events import should_notify_price_drop


class PriceDropLogicTests(unittest.TestCase):
    def test_significant_drop_at_five_percent(self):
        self.assertTrue(is_significant_price_drop(10_000, "USD", 9_500, "USD"))

    def test_ignores_small_drop(self):
        self.assertFalse(is_significant_price_drop(10_000, "USD", 9_600, "USD"))

    def test_ignores_price_increase(self):
        self.assertFalse(is_significant_price_drop(10_000, "USD", 10_500, "USD"))

    def test_extract_recent_drop_from_history(self):
        listing = SimpleNamespace(
            price=9000,
            currency="USD",
            price_history=[
                {
                    "price": 10000,
                    "currency": "USD",
                    "at": now_kyiv().isoformat(),
                }
            ],
        )
        info = extract_recent_price_drop(listing)
        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual(info.previous_price, 10000)
        self.assertEqual(info.drop_percent, 10.0)

    def test_old_history_not_recent(self):
        listing = SimpleNamespace(
            price=9000,
            currency="USD",
            price_history=[
                {
                    "price": 10000,
                    "currency": "USD",
                    "at": (now_kyiv() - timedelta(days=30)).isoformat(),
                }
            ],
        )
        self.assertIsNone(extract_recent_price_drop(listing))


class PriceDropNotifyDedupTests(unittest.IsolatedAsyncioTestCase):
    async def test_allows_first_drop(self):
        db = AsyncMock()
        db.scalar = AsyncMock(return_value=None)
        allowed = await should_notify_price_drop(
            db,
            user_id="u1",
            search_id="s1",
            listing_id="auto_ria_1",
            new_price=9000,
            new_currency="USD",
            drop_percent=10.0,
        )
        self.assertTrue(allowed)

    async def test_blocks_repeat_small_drop(self):
        db = AsyncMock()
        db.scalar = AsyncMock(
            return_value=SimpleNamespace(
                payload={"new_price": 9000, "currency": "USD"},
                type=NotificationType.price_drop,
            )
        )
        allowed = await should_notify_price_drop(
            db,
            user_id="u1",
            search_id="s1",
            listing_id="auto_ria_1",
            new_price=8700,
            new_currency="USD",
            drop_percent=3.0,
        )
        self.assertFalse(allowed)

    async def test_allows_second_significant_drop(self):
        db = AsyncMock()
        db.scalar = AsyncMock(
            return_value=SimpleNamespace(
                payload={"new_price": 9000, "currency": "USD"},
                type=NotificationType.price_drop,
            )
        )
        allowed = await should_notify_price_drop(
            db,
            user_id="u1",
            search_id="s1",
            listing_id="auto_ria_1",
            new_price=8000,
            new_currency="USD",
            drop_percent=11.1,
        )
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
