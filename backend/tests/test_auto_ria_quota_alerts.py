from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.services.auto_ria.quota_alerts import (
    _crossed_threshold,
    check_auto_ria_quota_alerts,
    is_auto_ria_quota_error,
    notify_auto_ria_quota_exhausted,
)
from app.services.auto_ria.quota_limits import resolve_auto_ria_quota_limits


class AutoRiaQuotaAlertTests(unittest.TestCase):
    def test_is_quota_error_403_package(self):
        body = 'У Вашому пакеті закінчились запити. Ви не можете робити запити на це API'
        self.assertTrue(is_auto_ria_quota_error(403, body))

    def test_is_not_quota_error_403_invalid_key(self):
        self.assertFalse(is_auto_ria_quota_error(403, "Invalid api_key"))

    def test_crossed_threshold(self):
        self.assertFalse(_crossed_threshold(799, 1000, 20))
        self.assertTrue(_crossed_threshold(800, 1000, 20))
        self.assertTrue(_crossed_threshold(900, 1000, 10))

    def test_resolve_max_package(self):
        monthly, hourly, key = resolve_auto_ria_quota_limits("1m", 1000, 30)
        self.assertEqual((monthly, hourly, key), (1_000_000, 20_000, "1m"))

    def test_max_package_no_hourly_alert_at_27_requests(self):
        monthly, hourly, _ = resolve_auto_ria_quota_limits("max", 0, 0)
        self.assertFalse(_crossed_threshold(27, hourly, 20))
        self.assertFalse(_crossed_threshold(27, hourly, 10))
        self.assertEqual(monthly, 1_000_000)

    def test_monthly_alert_at_20_percent_remaining(self):
        async def run():
            notify = AsyncMock()
            with (
                patch("app.services.auto_ria.quota_alerts.settings") as mock_settings,
                patch(
                    "app.services.auto_ria.quota_alerts.get_auto_ria_quota_usage",
                    AsyncMock(return_value={"hour_used": 5, "month_used": 800}),
                ),
                patch("app.services.auto_ria.quota_alerts._mark_sent", AsyncMock(return_value=True)),
                patch("app.services.auto_ria.quota_alerts.notify_monitor_admins", notify),
            ):
                mock_settings.AUTO_RIA_QUOTA_PACKAGE = ""
                mock_settings.AUTO_RIA_MONTHLY_QUOTA = 1000
                mock_settings.AUTO_RIA_HOURLY_QUOTA = 30
                mock_settings.AUTO_RIA_QUOTA_WARN_REMAINING = "20,10"
                await check_auto_ria_quota_alerts()
            self.assertTrue(notify.await_count >= 1)
            self.assertIn("20%", notify.await_args_list[0].args[0])

        import asyncio

        asyncio.run(run())

    def test_no_alert_when_max_package_and_low_usage(self):
        async def run():
            notify = AsyncMock()
            with (
                patch("app.services.auto_ria.quota_alerts.settings") as mock_settings,
                patch(
                    "app.services.auto_ria.quota_alerts.get_auto_ria_quota_usage",
                    AsyncMock(return_value={"hour_used": 27, "month_used": 500}),
                ),
                patch("app.services.auto_ria.quota_alerts._mark_sent", AsyncMock(return_value=True)),
                patch("app.services.auto_ria.quota_alerts.notify_monitor_admins", notify),
            ):
                mock_settings.AUTO_RIA_QUOTA_PACKAGE = "1m"
                mock_settings.AUTO_RIA_MONTHLY_QUOTA = 1000
                mock_settings.AUTO_RIA_HOURLY_QUOTA = 30
                mock_settings.AUTO_RIA_QUOTA_WARN_REMAINING = "20,10"
                await check_auto_ria_quota_alerts()
            notify.assert_not_awaited()

        import asyncio

        asyncio.run(run())

    def test_exhausted_alert(self):
        async def run():
            notify = AsyncMock()
            with (
                patch(
                    "app.services.auto_ria.quota_alerts.get_auto_ria_quota_usage",
                    AsyncMock(return_value={"hour_used": 30, "month_used": 1000}),
                ),
                patch("app.services.auto_ria.quota_alerts._exhausted_cooldown_ok", AsyncMock(return_value=True)),
                patch("app.services.auto_ria.quota_alerts.notify_monitor_admins", notify),
                patch("app.services.auto_ria.quota_alerts.settings") as mock_settings,
            ):
                mock_settings.AUTO_RIA_QUOTA_PACKAGE = ""
                mock_settings.AUTO_RIA_MONTHLY_QUOTA = 1000
                mock_settings.AUTO_RIA_HOURLY_QUOTA = 30
                await notify_auto_ria_quota_exhausted("AUTO.RIA помилка 403: пакет закінчився")
            notify.assert_awaited_once()
            self.assertIn("вичерпано", notify.await_args.args[0].lower())

        import asyncio

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
