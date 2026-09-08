"""Облік API на рівні моніторингу."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.admin.monitor_api_usage import (
    build_monitor_usage_report,
    estimate_monitor_api_per_live_fetch,
    estimate_monitor_daily_api,
    record_monitor_api_request,
    record_monitor_cycle,
    reset_monitor_search_ids,
    set_monitor_search_ids,
)
from storage.kv_store import SQLiteKV


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

    def test_estimate_all_scraper_sources(self):
        est = estimate_monitor_api_per_live_fetch(
            ["auto_ria", "olx", "car_market", "reono", "imperiya", "udrive", "telegram"],
        )
        self.assertIn("car_market", est["per_source"])
        self.assertIn("udrive", est["per_source"])
        self.assertIn("telegram_channels", est["per_source"])


class MonitorApiUsageStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_sqlite_storage_records_per_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            kv = SQLiteKV(Path(tmp) / "kv.db")
            with patch("app.services.admin.monitor_api_usage.get_redis", return_value=kv):
                token = set_monitor_search_ids(["search-1"])
                await record_monitor_api_request("auto_ria", "search", success=True, count=2)
                await record_monitor_api_request("udrive", "search", success=True)
                await record_monitor_api_request("imperiya", "search", success=False)
                await record_monitor_cycle(
                    ["search-1"],
                    event="live_api",
                    listings_found=5,
                    listings_new=1,
                )
                reset_monitor_search_ids(token)

                report = await build_monitor_usage_report("search-1", days=1)

        self.assertEqual(report["api_total"], 4)
        self.assertEqual(report["cycles"], 1)
        self.assertEqual(report["live_fetches"], 1)
        self.assertEqual(report["sources"]["auto_ria"]["total"], 2)
        self.assertEqual(report["sources"]["udrive"]["total"], 1)
        self.assertEqual(report["sources"]["imperiya"]["total"], 1)
        self.assertEqual(report["sources"]["imperiya"]["err"], 1)


if __name__ == "__main__":
    unittest.main()
