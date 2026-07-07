from __future__ import annotations

import re
import unittest

from parser.channel_links import is_numeric_channel_id, public_telegram_message_url


class ChannelLinksTests(unittest.TestCase):
    def test_numeric_channel_ids(self):
        self.assertTrue(is_numeric_channel_id("-1001482923083"))
        self.assertTrue(is_numeric_channel_id("1482923083"))
        self.assertFalse(is_numeric_channel_id("@ua_autobazar"))
        self.assertFalse(is_numeric_channel_id("CarsBidPro"))

    def test_public_url(self):
        self.assertEqual(
            public_telegram_message_url("ua_autobazar", 618510),
            "https://t.me/ua_autobazar/618510",
        )


if __name__ == "__main__":
    unittest.main()
