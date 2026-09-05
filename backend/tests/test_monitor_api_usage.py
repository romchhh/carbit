"""Облік API на рівні моніторингу."""

from __future__ import annotations

import unittest

from app.services.admin.monitor_api_usage import (
    estimate_monitor_api_per_live_fetch,
    estimate_monitor_daily_api,
)


class MonitorApiUsageTests(unittest.TestCase):
    def test_estimate_auto_ria_olx_per_fetch(self):
        est = estimate_monitor_api_per_live_fetch(["auto_ria", "olx"], category="all")
        self.assertEqual(est["per_source"]["auto_ria"]["total"], 42)
        self.assertEqual(est["per_source"]["olx"]["total"], 6)
        self.assertEqual(est["total"], 48)

    def test_estimate_daily_with_interval(self):
        est = estimate_monitor_daily_api(
            ["auto_ria"],
            category="used",
            interval_seconds=900,
        )
        self.assertEqual(est["cycles_per_day"], 96)
        self.assertEqual(est["estimated_live_fetches_per_day"], 96)
        self.assertEqual(est["estimated_api_per_day"], 96 * 41)


if __name__ == "__main__":
    unittest.main()
