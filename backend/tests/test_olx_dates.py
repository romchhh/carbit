from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from app.core.timezone import KYIV_TZ
from app.services.olx.dates import parse_olx_published_text, resolve_olx_published_at


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

    def test_prefers_last_refresh_time(self):
        raw = {
            "createdTime": "2024-10-28T14:04:07+02:00",
            "lastRefreshTime": "2026-06-22T00:07:18+03:00",
        }
        dt = resolve_olx_published_at(published=None, raw_params=raw, now=self.now)
        self.assertEqual(dt, datetime(2026, 6, 22, 0, 7, 18, tzinfo=KYIV_TZ))

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


if __name__ == "__main__":
    unittest.main()
