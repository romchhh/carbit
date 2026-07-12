from __future__ import annotations

import unittest

from app.services.telegram_channels.channels import normalize_channel_username


class TelegramChannelNormalizeTests(unittest.TestCase):
    def test_username(self):
        self.assertEqual(normalize_channel_username("ua_autobazar"), "@ua_autobazar")
        self.assertEqual(normalize_channel_username("@CarsBidPro"), "@CarsBidPro")

    def test_url(self):
        self.assertEqual(
            normalize_channel_username("https://t.me/auto_amerika_europa"),
            "@auto_amerika_europa",
        )

    def test_rejects_numeric(self):
        with self.assertRaises(ValueError):
            normalize_channel_username("-100123")


if __name__ == "__main__":
    unittest.main()
