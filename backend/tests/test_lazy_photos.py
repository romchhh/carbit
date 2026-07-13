from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class LazyPhotosEnqueueTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.services.telegram_channels.bootstrap import ensure_parser_path

        ensure_parser_path()
        from parser.channel_media_store import ChannelMediaStore

        self._tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmp.name) / "media.db")
        self.store = ChannelMediaStore(db_path=self.db)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_enqueue_synthesizes_refs_from_listing_id(self) -> None:
        from app.services.telegram_channels import lazy_photos

        with patch.object(lazy_photos, "_media_store", return_value=self.store):
            ok = lazy_photos.enqueue_listing_photos("telegram_ua_autobazar_555")
        self.assertTrue(ok)
        refs = self.store.get_photo_refs("telegram_ua_autobazar_555")
        self.assertIsNotNone(refs)
        self.assertEqual(refs[0], "@ua_autobazar")
        self.assertEqual(refs[1], [555])
        self.assertEqual(self.store.claim_photo_jobs(limit=1), ["telegram_ua_autobazar_555"])

    def test_listing_needs_photos(self) -> None:
        from app.services.telegram_channels import lazy_photos

        listing = type(
            "L",
            (),
            {"id": "telegram_x_1", "source": "telegram", "images": []},
        )()
        with patch.object(lazy_photos, "_media_store", return_value=self.store):
            self.assertTrue(lazy_photos.listing_needs_photos(listing))
            listing.images = ["https://example.com/a.jpg"]
            self.assertFalse(lazy_photos.listing_needs_photos(listing))


if __name__ == "__main__":
    unittest.main()
