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
            # URL в БД є, файлу на диску немає — треба качати знову
            listing.images = ["/api/v1/telegram-media/missing/1.jpg"]
            self.assertTrue(lazy_photos.listing_needs_photos(listing))

    def test_load_existing_photo_urls_from_disk(self) -> None:
        from app.core.config import settings
        from app.services.telegram_channels import lazy_photos

        media_root = Path(settings.TELEGRAM_MEDIA_DIR) / "ua_autobazar"
        media_root.mkdir(parents=True, exist_ok=True)
        photo = media_root / "777.jpg"
        photo.write_bytes(b"\xff\xd8\xff")

        self.store.save_photo_refs("telegram_ua_autobazar_777", "@ua_autobazar", [777])
        with patch.object(lazy_photos, "_media_store", return_value=self.store):
            urls = lazy_photos.load_existing_telegram_photo_urls(
                "telegram_ua_autobazar_777",
                limit=1,
            )
        self.assertEqual(len(urls), 1)
        self.assertIn("/api/v1/telegram-media/", urls[0])
        photo.unlink(missing_ok=True)


class EnsureTelegramPhotosTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_online_skips_inline_telethon(self) -> None:
        from app.models.models import Listing, Source
        from app.services.telegram_channels import lazy_photos

        listing = Listing(
            id="telegram_ua_autobazar_999",
            source=Source.telegram,
            title="Test",
            images=[],
        )
        db = unittest.mock.AsyncMock()

        with (
            patch.object(lazy_photos, "sync_telegram_photos_from_disk", return_value=[]),
            patch.object(lazy_photos, "listing_needs_photos", return_value=True),
            patch.object(lazy_photos, "enqueue_listing_photos", return_value=True) as enqueue,
            patch.object(lazy_photos, "telegram_worker_online", return_value=True),
            patch.object(lazy_photos, "wait_for_listing_photos", return_value=[]),
            patch.object(lazy_photos, "attach_photos_to_listing") as attach,
        ):
            urls = await lazy_photos.ensure_telegram_listing_photos(db, listing)

        self.assertEqual(urls, [])
        attach.assert_not_called()
        self.assertGreaterEqual(enqueue.call_count, 2)

    async def test_worker_offline_uses_inline_telethon(self) -> None:
        from app.models.models import Listing, Source
        from app.services.telegram_channels import lazy_photos

        listing = Listing(
            id="telegram_ua_autobazar_1001",
            source=Source.telegram,
            title="Test",
            images=[],
        )
        db = unittest.mock.AsyncMock()
        expected = ["/api/v1/telegram-media/ua_autobazar/1001.jpg"]

        async def _download(*_args, **_kwargs):
            return expected

        class FakeService:
            async def start(self) -> None:
                return None

            async def stop(self) -> None:
                return None

        with (
            patch.object(lazy_photos, "sync_telegram_photos_from_disk", return_value=[]),
            patch.object(lazy_photos, "listing_needs_photos", return_value=True),
            patch.object(lazy_photos, "enqueue_listing_photos", return_value=True),
            patch.object(lazy_photos, "telegram_worker_online", return_value=False),
            patch(
                "app.services.telegram_channels.service_loader.get_parser_service",
                return_value=FakeService(),
            ),
            patch.object(lazy_photos, "attach_photos_to_listing", side_effect=_download) as attach,
        ):
            urls = await lazy_photos.ensure_telegram_listing_photos(db, listing)

        attach.assert_called_once()
        self.assertEqual(urls, expected)


if __name__ == "__main__":
    unittest.main()
