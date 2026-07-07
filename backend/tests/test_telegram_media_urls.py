from __future__ import annotations

import unittest
from pathlib import Path

from app.core.config import settings
from app.services.telegram.media_urls import (
    resolve_listing_image_url,
    telegram_media_local_path,
)


class TelegramMediaUrlTests(unittest.TestCase):
    def test_resolve_relative_api_path(self):
        url = resolve_listing_image_url("/api/v1/telegram-media/CarsBidPro/14109.jpg")
        self.assertIn("/api/v1/telegram-media/CarsBidPro/14109.jpg", url or "")
        self.assertTrue(str(url).startswith("http"))

    def test_local_path_from_api_url(self):
        sample = Path(settings.TELEGRAM_MEDIA_DIR) / "CarsBidPro" / "14109.jpg"
        if sample.is_file():
            path = telegram_media_local_path("/api/v1/telegram-media/CarsBidPro/14109.jpg")
            self.assertEqual(path, sample.resolve())


if __name__ == "__main__":
    unittest.main()
