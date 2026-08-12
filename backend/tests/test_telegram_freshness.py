"""Тести вікна свіжості Telegram (строк зберігання, типово 4 місяці)."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.core.timezone import KYIV_TZ, now_kyiv
from app.schemas.schemas import SearchFilters
from app.services.telegram_channels.freshness import (
    TELEGRAM_LISTING_MAX_AGE_DAYS,
    telegram_listing_is_fresh,
    telegram_published_cutoff,
)
from app.services.telegram_channels.mapper import listing_out_matches_filters
from parser.freshness import message_date_is_fresh, telegram_scan_cutoff_utc


class TelegramFreshnessTests(unittest.TestCase):
    def test_max_age_is_four_months(self):
        self.assertEqual(TELEGRAM_LISTING_MAX_AGE_DAYS, 120)

    def test_scan_and_serve_windows_agree(self):
        """Парсер і бекенд мають різати за однаковим строком."""
        from parser.freshness import TELEGRAM_LISTING_MAX_AGE_DAYS as parser_days

        self.assertEqual(parser_days, TELEGRAM_LISTING_MAX_AGE_DAYS)

    def test_fresh_listing_passes(self):
        published = now_kyiv() - timedelta(days=10)
        self.assertTrue(telegram_listing_is_fresh(published))

    def test_old_listing_rejected(self):
        published = now_kyiv() - timedelta(days=150)
        self.assertFalse(telegram_listing_is_fresh(published))

    def test_cutoff_matches_max_age(self):
        cutoff = telegram_published_cutoff()
        self.assertLessEqual(
            abs((now_kyiv() - cutoff).days - TELEGRAM_LISTING_MAX_AGE_DAYS),
            1,
        )

    def test_filter_rejects_old_telegram_post(self):
        old = now_kyiv() - timedelta(days=400)
        item = type(
            "Item",
            (),
            {
                "brand": "Mini",
                "model": "Countryman",
                "title": "Mini Countryman 2013",
                "year": 2013,
                "price": 10600,
                "currency": "USD",
                "mileage": 140000,
                "region": "Україна",
                "source": "telegram",
                "fuel": "Бензин",
                "transmission": "Автомат",
                "description": "Mini Countryman",
                "published_at": old,
                "found_at": old,
            },
        )()
        filters = SearchFilters.model_validate({"brand": "Mini", "sources": ["telegram"]})
        self.assertFalse(listing_out_matches_filters(item, filters))

    def test_filter_keeps_recent_telegram_post(self):
        recent = now_kyiv() - timedelta(days=20)
        item = type(
            "Item",
            (),
            {
                "brand": "Mini",
                "model": "Countryman",
                "title": "Mini Countryman 2016",
                "year": 2016,
                "price": 12000,
                "currency": "USD",
                "mileage": 80000,
                "region": "Київ",
                "source": "telegram",
                "fuel": "",
                "transmission": "",
                "description": "Mini Countryman",
                "published_at": recent,
                "found_at": recent,
            },
        )()
        filters = SearchFilters.model_validate({"brand": "Mini", "sources": ["telegram"]})
        self.assertTrue(listing_out_matches_filters(item, filters))

    def test_parser_message_date_window(self):
        cutoff = telegram_scan_cutoff_utc()
        fresh = datetime.now(timezone.utc) - timedelta(days=5)
        old = datetime.now(timezone.utc) - timedelta(days=200)
        self.assertTrue(message_date_is_fresh(fresh, cutoff=cutoff))
        self.assertFalse(message_date_is_fresh(old, cutoff=cutoff))


if __name__ == "__main__":
    unittest.main()
