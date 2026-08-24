"""Тести системного моніторингу."""

from __future__ import annotations

import unittest

from app.core.config import monitor_admin_chat_ids
from app.services.monitoring.parser_status import normalize_parser_source
from app.services.monitoring.collect import format_status_message
from app.services.monitoring.models import ComponentStatus, HealthLevel, SystemStatus


class MonitorConfigTests(unittest.TestCase):
    def test_monitor_admin_ids_parses_csv(self):
        from app.core import config

        original = config.settings.MONITOR_ADMIN_IDS
        try:
            config.settings.MONITOR_ADMIN_IDS = "1734355788, 7119952932"
            self.assertEqual(monitor_admin_chat_ids(), ["1734355788", "7119952932"])
        finally:
            config.settings.MONITOR_ADMIN_IDS = original


class MonitorFormatTests(unittest.TestCase):
    def test_format_status_message_lists_parsers(self):
        status = SystemStatus(
            components=[
                ComponentStatus("backend", "Backend API", HealthLevel.OK, "OK"),
                ComponentStatus("parser:auto_ria", "AUTO.RIA", HealthLevel.OK, "10 огол."),
                ComponentStatus("parser:olx", "OLX", HealthLevel.DOWN, "timeout"),
            ],
            checked_at=0,
        )
        text = format_status_message(status, title="Test")
        self.assertIn("AUTO.RIA", text)
        self.assertIn("OLX", text)
        self.assertIn("Потребує уваги", text)


class ParserSourceNormalizeTests(unittest.TestCase):
    def test_normalize_display_names(self):
        self.assertEqual(normalize_parser_source("AUTO.RIA"), "auto_ria")
        self.assertEqual(normalize_parser_source("Імперія Авто"), "imperiya")
        self.assertEqual(normalize_parser_source("car_market"), "car_market")


if __name__ == "__main__":
    unittest.main()
