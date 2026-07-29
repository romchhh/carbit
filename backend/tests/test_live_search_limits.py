"""Live search hourly limits by plan."""

from __future__ import annotations

import unittest

from app.services.billing.plans import PLANS, get_plan


class LiveSearchesHourTests(unittest.TestCase):
    def test_plan_values(self):
        self.assertEqual(get_plan("free")["live_searches_hour"], 30)
        self.assertEqual(get_plan("lite")["live_searches_hour"], 150)
        self.assertEqual(get_plan("standard")["live_searches_hour"], 300)
        self.assertEqual(get_plan("pro")["live_searches_hour"], 600)

    def test_paid_higher_than_free(self):
        free = PLANS["free"]["live_searches_hour"]
        for plan_id in ("lite", "standard", "pro"):
            self.assertGreater(PLANS[plan_id]["live_searches_hour"], free)


if __name__ == "__main__":
    unittest.main()
