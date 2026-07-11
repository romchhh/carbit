import unittest
from datetime import timedelta

from app.core.timezone import now_kyiv
from app.services.auto_ria.constants import AUTO_RIA_TOP_3H, AUTO_RIA_TOP_HOUR
from app.services.notifications.freshness import (
    auto_ria_top_for_max_hours,
    coerce_notification_max_hours,
    is_listing_fresh_for_notification,
)


class NotificationFreshnessTests(unittest.TestCase):
    def test_fresh_within_one_hour(self):
        now = now_kyiv()
        published = now - timedelta(minutes=45)
        self.assertTrue(is_listing_fresh_for_notification(published, max_hours=1, now=now))

    def test_stale_after_one_hour(self):
        now = now_kyiv()
        published = now - timedelta(hours=1, minutes=5)
        self.assertFalse(is_listing_fresh_for_notification(published, max_hours=1, now=now))

    def test_stale_one_day_old(self):
        now = now_kyiv()
        published = now - timedelta(days=1)
        self.assertFalse(is_listing_fresh_for_notification(published, max_hours=1, now=now))
        self.assertFalse(is_listing_fresh_for_notification(published, max_hours=2, now=now))

    def test_missing_published_at(self):
        self.assertFalse(is_listing_fresh_for_notification(None, max_hours=1))

    def test_coerce_hours(self):
        self.assertEqual(coerce_notification_max_hours("2"), 2.0)
        self.assertEqual(coerce_notification_max_hours(None), 1.0)
        self.assertEqual(coerce_notification_max_hours(-1), 1.0)

    def test_auto_ria_top_mapping(self):
        self.assertEqual(auto_ria_top_for_max_hours(1), AUTO_RIA_TOP_HOUR)
        self.assertEqual(auto_ria_top_for_max_hours(2), AUTO_RIA_TOP_3H)


if __name__ == "__main__":
    unittest.main()
