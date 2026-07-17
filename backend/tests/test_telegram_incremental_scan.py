from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.core.timezone import KYIV_TZ
from app.services.telegram_channels.ingest import telegram_found_after_cutoff


def _search(*, last_checked_at: datetime | None) -> MagicMock:
    row = MagicMock()
    row.last_checked_at = last_checked_at
    return row


class TelegramIncrementalScanTests(unittest.TestCase):
    def test_uses_min_last_checked_when_all_set(self):
        t1 = datetime(2026, 7, 17, 10, 0, tzinfo=KYIV_TZ)
        t2 = datetime(2026, 7, 17, 11, 0, tzinfo=KYIV_TZ)
        cutoff = telegram_found_after_cutoff(
            [_search(last_checked_at=t2), _search(last_checked_at=t1)],
            max_hours=1,
        )
        self.assertEqual(cutoff, t1)

    def test_falls_back_to_hours_window_when_never_checked(self):
        before = datetime.now(KYIV_TZ)
        cutoff = telegram_found_after_cutoff(
            [_search(last_checked_at=None)],
            max_hours=2,
        )
        after = datetime.now(KYIV_TZ)
        self.assertGreater(cutoff, before - timedelta(hours=2, minutes=1))
        self.assertLess(cutoff, after - timedelta(hours=1, minutes=59))

    def test_empty_searches_use_hours_window(self):
        cutoff = telegram_found_after_cutoff([], max_hours=1)
        self.assertGreater(cutoff, datetime.now(KYIV_TZ) - timedelta(hours=2))


if __name__ == "__main__":
    unittest.main()
