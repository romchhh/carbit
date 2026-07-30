"""Тести purge застарілих Telegram-оголошень."""

from __future__ import annotations

import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.timezone import now_kyiv
from app.services.telegram_channels.freshness import TELEGRAM_LISTING_MAX_AGE_DAYS
from app.services.telegram_channels.purge import purge_stale_telegram_listings


class TelegramPurgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_purge_deletes_old_ids(self):
        stale_id = "telegram_old_1"
        db = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = [stale_id]
        db.scalars = AsyncMock(return_value=scalars_result)
        db.execute = AsyncMock()

        with patch(
            "app.services.telegram_channels.purge.telegram_published_cutoff",
            return_value=now_kyiv() - timedelta(days=TELEGRAM_LISTING_MAX_AGE_DAYS),
        ):
            deleted = await purge_stale_telegram_listings(db)

        self.assertEqual(deleted, 1)
        self.assertEqual(db.execute.await_count, 2)  # unlink duplicate_of + delete

    async def test_purge_noop_when_empty(self):
        db = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = []
        db.scalars = AsyncMock(return_value=scalars_result)
        db.execute = AsyncMock()

        deleted = await purge_stale_telegram_listings(db)
        self.assertEqual(deleted, 0)
        db.execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
