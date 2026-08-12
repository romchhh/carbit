"""Прибирання фото повідомлень, які так і не стали оголошеннями."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.telegram_channels.media_cleanup import delete_orphan_photo_refs


def _store(orphans: dict, total: int) -> MagicMock:
    store = MagicMock()
    store.orphan_photo_refs.return_value = orphans
    store.photo_refs_count.return_value = total
    return store


class OrphanPhotoRefsTests(unittest.TestCase):
    def _run(self, store: MagicMock, live: set[str]) -> int:
        with patch.dict(
            "sys.modules",
            {"parser.channel_media_store": MagicMock(ChannelMediaStore=lambda: store)},
        ):
            return delete_orphan_photo_refs(live)

    def test_removes_orphans(self):
        store = _store({"telegram_ch_9": ("@ch", [9])}, total=10)
        removed = self._run(store, {"telegram_ch_1"})
        self.assertEqual(removed, 1)
        store.delete_photo_refs.assert_called_once_with(["telegram_ch_9"])

    def test_empty_live_set_is_never_a_full_wipe(self):
        """Збій вибірки оголошень не має стирати весь кеш фото."""
        store = _store({f"telegram_ch_{i}": ("@ch", [i]) for i in range(50)}, total=50)
        self.assertEqual(self._run(store, set()), 0)
        store.delete_photo_refs.assert_not_called()

    def test_skips_when_almost_everything_looks_orphaned(self):
        store = _store({f"telegram_ch_{i}": ("@ch", [i]) for i in range(95)}, total=100)
        self.assertEqual(self._run(store, {"telegram_live_1"}), 0)
        store.delete_photo_refs.assert_not_called()

    def test_nothing_to_do(self):
        store = _store({}, total=10)
        self.assertEqual(self._run(store, {"telegram_ch_1"}), 0)
        store.delete_photo_refs.assert_not_called()


if __name__ == "__main__":
    unittest.main()
