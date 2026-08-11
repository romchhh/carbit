from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from app.core.timezone import KYIV_TZ
from app.services.olx.dates import (
    parse_olx_published_text,
    resolve_olx_published_at,
    resolve_olx_refreshed_at,
)


class OlxPublishedDateTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 7, 15, 30, tzinfo=KYIV_TZ)

    def test_minutes_ago(self):
        dt = parse_olx_published_text("5 хвилин тому", now=self.now)
        self.assertEqual(dt, self.now - timedelta(minutes=5))

    def test_hours_ago(self):
        dt = parse_olx_published_text("1 годину тому", now=self.now)
        self.assertEqual(dt, self.now - timedelta(hours=1))

    def test_today_with_time(self):
        dt = parse_olx_published_text("сьогодні о 14:30", now=self.now)
        self.assertEqual(dt, self.now.replace(hour=14, minute=30, second=0, microsecond=0))

    def test_yesterday(self):
        dt = parse_olx_published_text("вчора о 09:15", now=self.now)
        expected = (self.now - timedelta(days=1)).replace(hour=9, minute=15, second=0, microsecond=0)
        self.assertEqual(dt, expected)

    def test_month_name(self):
        dt = parse_olx_published_text("3 липня 2026", now=self.now)
        self.assertEqual(dt, datetime(2026, 7, 3, 12, 0, tzinfo=KYIV_TZ))

    def test_month_name_with_year_suffix(self):
        dt = parse_olx_published_text("10 липня 2026 р.", now=self.now)
        self.assertEqual(dt, datetime(2026, 7, 10, 12, 0, tzinfo=KYIV_TZ))

    def test_published_label_prefix(self):
        dt = parse_olx_published_text("Опубліковано 10 липня 2026 р.", now=self.now)
        self.assertEqual(dt, datetime(2026, 7, 10, 12, 0, tzinfo=KYIV_TZ))

    def test_glued_published_today_without_space(self):
        # OLX get_text(strip=True) зливає «Опубліковано» + «сьогодні о 08:21»
        dt = parse_olx_published_text("Опублікованосьогодні о 08:21", now=self.now)
        self.assertEqual(dt, self.now.replace(hour=8, minute=21, second=0, microsecond=0))

    def test_resolve_glued_text_does_not_fallback_to_now(self):
        dt = resolve_olx_published_at(
            published="Опублікованосьогодні о 08:21",
            raw_params={},
            now=self.now,
        )
        self.assertEqual(dt, self.now.replace(hour=8, minute=21, second=0, microsecond=0))

    def test_published_prefers_created_time(self):
        raw = {
            "createdTime": "2024-10-28T14:04:07+02:00",
            "lastRefreshTime": "2026-06-22T00:07:18+03:00",
        }
        dt = resolve_olx_published_at(published=None, raw_params=raw, now=self.now)
        self.assertEqual(dt, datetime(2024, 10, 28, 14, 4, 7, tzinfo=KYIV_TZ))

    def test_refreshed_uses_last_refresh_time(self):
        raw = {
            "createdTime": "2024-10-28T14:04:07+02:00",
            "lastRefreshTime": "2026-06-22T00:07:18+03:00",
        }
        published = resolve_olx_published_at(published=None, raw_params=raw, now=self.now)
        refreshed = resolve_olx_refreshed_at(
            raw_params=raw,
            published_at=published,
            now=self.now,
        )
        self.assertEqual(refreshed, datetime(2026, 6, 22, 0, 7, 18, tzinfo=KYIV_TZ))

    def test_created_time_from_raw_params(self):
        raw = {"createdTime": "2026-06-15T10:00:00+03:00"}
        dt = resolve_olx_published_at(published=None, raw_params=raw, now=self.now)
        self.assertEqual(dt, datetime(2026, 6, 15, 10, 0, tzinfo=KYIV_TZ))

    def test_location_date_tail(self):
        dt = resolve_olx_published_at(
            published="Київ - 12 хвилин тому",
            raw_params={},
            now=self.now,
        )
        self.assertEqual(dt, self.now - timedelta(minutes=12))

    def test_does_not_prefer_refresh_over_card_date_text(self):
        refresh = "2026-07-14T12:00:00+03:00"
        dt = resolve_olx_published_at(
            published="Київ - 3 липня 2026",
            raw_params={"lastRefreshTime": refresh},
            now=self.now,
        )
        self.assertEqual(dt, datetime(2026, 7, 3, 12, 0, tzinfo=KYIV_TZ))

    def test_refresh_iso_alone_without_created_falls_back_to_iso(self):
        """Немає createdTime — беремо ISO з поля published (краще ніж «зараз»)."""
        refresh = "2026-06-22T00:07:18+03:00"
        dt = resolve_olx_published_at(
            published=refresh,
            raw_params={"lastRefreshTime": refresh},
            now=self.now,
        )
        self.assertEqual(dt, datetime(2026, 6, 22, 0, 7, 18, tzinfo=KYIV_TZ))

    def test_created_beats_refresh_in_raw(self):
        raw = {
            "createdTime": "2025-01-10T08:00:00+02:00",
            "lastRefreshTime": "2026-07-14T12:00:00+03:00",
        }
        dt = resolve_olx_published_at(
            published="2026-07-14T12:00:00+03:00",
            raw_params=raw,
            now=self.now,
        )
        self.assertEqual(dt, datetime(2025, 1, 10, 8, 0, tzinfo=KYIV_TZ))

    def test_combined_updated_published_text(self):
        published = resolve_olx_published_at(
            published="Оновлено 4 год тому • Опубліковано 4 тиж тому",
            raw_params={},
            now=self.now,
        )
        refreshed = resolve_olx_refreshed_at(
            published="Оновлено 4 год тому • Опубліковано 4 тиж тому",
            published_at=published,
            raw_params={},
            now=self.now,
        )
        self.assertEqual(published, self.now - timedelta(weeks=4))
        self.assertEqual(refreshed, self.now - timedelta(hours=4))


if __name__ == "__main__":
    unittest.main()
