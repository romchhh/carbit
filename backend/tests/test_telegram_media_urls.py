from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.telegram.media_urls import (
    filter_existing_image_urls,
    resolve_listing_image_url,
    telegram_media_local_path,
)


class TelegramMediaUrlTests(unittest.TestCase):
    def test_resolve_relative_api_path(self):
        url = resolve_listing_image_url("/api/v1/telegram-media/CarsBidPro/14109.jpg")
        self.assertIn("/api/v1/telegram-media/CarsBidPro/14109.jpg", url or "")
        self.assertTrue(str(url).startswith("http"))

    def test_filter_drops_missing_telegram_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "CarsBidPro" / "1.jpg"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"jpeg")
            missing_url = "/api/v1/telegram-media/CarsBidPro/999.jpg"
            ok_url = "/api/v1/telegram-media/CarsBidPro/1.jpg"
            remote = "https://cdn.example.com/car.jpg"
            with patch("app.services.telegram.media_urls.settings") as settings:
                settings.TELEGRAM_MEDIA_DIR = str(root)
                filtered = filter_existing_image_urls([missing_url, ok_url, remote, ""])
                self.assertEqual(filtered, [ok_url, remote])
                self.assertIsNone(telegram_media_local_path(missing_url))
                self.assertEqual(telegram_media_local_path(ok_url), existing)


if __name__ == "__main__":
    unittest.main()
