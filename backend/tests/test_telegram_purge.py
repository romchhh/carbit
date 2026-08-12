"""Тести строку зберігання: старі оголошення видаляються разом із фото."""

from __future__ import annotations

import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.timezone import now_kyiv
from app.services.listings.retention import purge_stale_listings
from app.services.telegram_channels.freshness import TELEGRAM_LISTING_MAX_AGE_DAYS


def _db_with_stale(ids: list[str]) -> AsyncMock:
    db = AsyncMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = ids
    db.scalars = AsyncMock(return_value=scalars_result)
    db.execute = AsyncMock()
    return db


class ListingRetentionTests(unittest.IsolatedAsyncioTestCase):
    async def test_purge_deletes_old_ids(self):
        db = _db_with_stale(["telegram_old_1"])

        with (
            patch(
                "app.services.listings.retention.telegram_published_cutoff",
                return_value=now_kyiv() - timedelta(days=TELEGRAM_LISTING_MAX_AGE_DAYS),
            ),
            patch("app.services.listings.retention.delete_media_for_listing_ids") as media,
            patch("app.services.listings.retention.purge_stale_media_files"),
        ):
            deleted = await purge_stale_listings(db)

        self.assertEqual(deleted, 1)
        self.assertEqual(db.execute.await_count, 2)  # unlink duplicate_of + delete
        media.assert_called_once_with(["telegram_old_1"])

    async def test_purge_covers_all_sources(self):
        """OLX / AUTO.RIA раніше не чистились узагалі."""
        stale = ["olx_1", "auto_ria_2", "telegram_ch_3"]
        db = _db_with_stale(stale)

        with (
            patch("app.services.listings.retention.delete_media_for_listing_ids") as media,
            patch("app.services.listings.retention.purge_stale_media_files"),
        ):
            deleted = await purge_stale_listings(db)

        self.assertEqual(deleted, 3)
        # Локальні файли є лише в Telegram — решта тримає зовнішні URL.
        media.assert_called_once_with(["telegram_ch_3"])

    async def test_purge_without_telegram_skips_media(self):
        db = _db_with_stale(["olx_1"])

        with (
            patch("app.services.listings.retention.delete_media_for_listing_ids") as media,
            patch("app.services.listings.retention.purge_stale_media_files"),
        ):
            deleted = await purge_stale_listings(db)

        self.assertEqual(deleted, 1)
        media.assert_not_called()

    async def test_purge_noop_when_empty(self):
        db = _db_with_stale([])
        deleted = await purge_stale_listings(db)
        self.assertEqual(deleted, 0)
        db.execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
