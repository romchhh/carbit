from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class ChannelMediaStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.services.telegram_channels.bootstrap import ensure_parser_path

        ensure_parser_path()
        from parser.channel_media_store import ChannelMediaStore

        self._tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmp.name) / "media.db")
        self.store = ChannelMediaStore(db_path=self.db)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_cursor_starts_at_zero_and_advances(self) -> None:
        self.assertEqual(self.store.get_cursor("@cars"), 0)
        self.store.advance_cursor("@cars", 10)
        self.assertEqual(self.store.get_cursor("@cars"), 10)
        self.store.advance_cursor("@cars", 7)
        self.assertEqual(self.store.get_cursor("@cars"), 10)
        self.store.advance_cursor("@cars", 42)
        self.assertEqual(self.store.get_cursor("@cars"), 42)

    def test_photo_refs_and_queue(self) -> None:
        lid = "telegram_ua_autobazar_100"
        self.store.save_photo_refs(lid, "@ua_autobazar", [100, 101, 102])
        refs = self.store.get_photo_refs(lid)
        self.assertIsNotNone(refs)
        channel, ids, status = refs
        self.assertEqual(channel, "@ua_autobazar")
        self.assertEqual(ids, [100, 101, 102])
        self.assertEqual(status, "pending")

        self.assertTrue(self.store.enqueue_photo_download(lid))
        self.assertTrue(self.store.enqueue_photo_download(lid))  # idempotent
        jobs = self.store.claim_photo_jobs(limit=5)
        self.assertEqual(jobs, [lid])

        self.store.mark_photos_done(lid)
        self.assertEqual(self.store.get_photo_refs(lid)[2], "done")
        self.assertFalse(self.store.enqueue_photo_download(lid))
        self.assertEqual(self.store.claim_photo_jobs(limit=5), [])

    def test_enqueue_without_refs_returns_false(self) -> None:
        self.assertFalse(self.store.enqueue_photo_download("telegram_missing_1"))

    def test_force_requeues_done_listing(self) -> None:
        """Файли зникли з диска — 'done' не має блокувати перезавантаження."""
        lid = "telegram_ua_autobazar_200"
        self.store.save_photo_refs(lid, "@ua_autobazar", [200])
        self.store.mark_photos_done(lid)
        self.assertFalse(self.store.enqueue_photo_download(lid))

        self.assertTrue(self.store.enqueue_photo_download(lid, force=True))
        self.assertEqual(self.store.get_photo_refs(lid)[2], "pending")
        self.assertEqual(self.store.claim_photo_jobs(limit=5), [lid])

    def test_force_requeues_failed_listing(self) -> None:
        lid = "telegram_ua_autobazar_300"
        self.store.save_photo_refs(lid, "@ua_autobazar", [300])
        self.store.mark_photos_failed(lid)
        self.assertTrue(self.store.enqueue_photo_download(lid))
        self.assertEqual(self.store.get_photo_refs(lid)[2], "pending")

    def test_album_message_ids_for_cleanup(self) -> None:
        """Видаляючи оголошення, треба знати всі фото альбому, не лише перше."""
        lid = "telegram_ua_autobazar_400"
        self.store.save_photo_refs(lid, "@ua_autobazar", [400, 401, 402])
        refs = self.store.all_photo_message_ids([lid, "telegram_missing_1"])
        self.assertEqual(refs, {lid: ("@ua_autobazar", [400, 401, 402])})

    def test_delete_photo_refs_clears_queue(self) -> None:
        lid = "telegram_ua_autobazar_500"
        self.store.save_photo_refs(lid, "@ua_autobazar", [500])
        self.store.enqueue_photo_download(lid)
        self.assertEqual(self.store.photo_queue_pending_count(), 1)

        self.assertEqual(self.store.delete_photo_refs([lid]), 1)
        self.assertIsNone(self.store.get_photo_refs(lid))
        self.assertEqual(self.store.photo_queue_pending_count(), 0)


if __name__ == "__main__":
    unittest.main()
