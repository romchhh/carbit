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


if __name__ == "__main__":
    unittest.main()
