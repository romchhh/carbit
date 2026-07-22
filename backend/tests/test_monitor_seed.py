"""Тести seed baseline для моніторингів."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.timezone import KYIV_TZ, now_kyiv
from app.schemas.schemas import ListingOut


def _listing(**kwargs) -> ListingOut:
    base = dict(
        id="auto_ria_1",
        source="auto_ria",
        title="BMW 320",
        brand="BMW",
        model="320",
        year=2019,
        price=15000,
        currency="USD",
        mileage=80000,
        fuel="Бензин",
        transmission="Автомат",
        region="Київ",
        description=None,
        images=[],
        url="https://example.com",
        seller_type="private",
        vin=None,
        source_data=None,
        price_history=[],
        is_duplicate=False,
        published_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
        found_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
    )
    base.update(kwargs)
    return ListingOut(**base)


class SeedBaselineTests(unittest.IsolatedAsyncioTestCase):
    async def test_seed_does_not_increment_new_count(self):
        from app.services.parser.linking import seed_search_baseline

        search = MagicMock()
        search.id = "search-1"
        search.new_count = 0
        search.total_count = 0

        listing = MagicMock()
        listing.id = "auto_ria_1"

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=None)
        db.add = MagicMock()
        db.flush = AsyncMock()

        with patch(
            "app.services.listings.upsert.upsert_listing_with_mirrors",
            AsyncMock(return_value=listing),
        ):
            linked = await seed_search_baseline(db, search, [_listing()])

        self.assertEqual(linked, 1)
        self.assertEqual(search.new_count, 0)
        self.assertEqual(search.total_count, 1)
        added = db.add.call_args[0][0]
        self.assertFalse(added.is_new)

    async def test_seed_passes_alternate_sources_to_upsert(self):
        from app.schemas.schemas import ListingSourceLink
        from app.services.parser.linking import seed_search_baseline

        search = MagicMock()
        search.id = "search-1"
        search.new_count = 0
        search.total_count = 0

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=None)
        db.add = MagicMock()
        db.flush = AsyncMock()

        upsert = AsyncMock(side_effect=lambda _db, data: MagicMock(id=data.id))
        with patch("app.services.listings.upsert.upsert_listing_with_mirrors", upsert):
            linked = await seed_search_baseline(
                db,
                search,
                [
                    _listing(
                        alternate_sources=[
                            ListingSourceLink(
                                source="olx",
                                url="https://olx.example/1",
                                id="olx_1",
                            )
                        ]
                    )
                ],
            )

        self.assertEqual(linked, 1)
        self.assertEqual(upsert.await_count, 1)
        payload = upsert.await_args.args[1]
        self.assertEqual(payload.id, "auto_ria_1")
        self.assertEqual(len(payload.alternate_sources), 1)
        self.assertEqual(payload.alternate_sources[0].id, "olx_1")


class LinkFreshnessTests(unittest.IsolatedAsyncioTestCase):
    async def test_stale_listing_not_new_and_no_notify(self):
        from app.services.parser.linking import link_listing_to_search

        search = MagicMock()
        search.id = "search-1"
        search.user_id = "user-1"
        search.new_count = 0
        search.total_count = 0

        listing = MagicMock()
        listing.id = "auto_ria_old"
        listing.published_at = now_kyiv() - timedelta(days=4)

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=None)
        db.get = AsyncMock(return_value=listing)
        db.add = MagicMock()
        db.flush = AsyncMock()

        with patch(
            "app.services.parser.linking.notify_monitor_listing_after_link",
            AsyncMock(return_value=True),
        ) as notify:
            is_new, sent = await link_listing_to_search(
                db,
                search=search,
                listing_id=listing.id,
                notify=True,
                user=MagicMock(id="user-1"),
                max_notification_hours=6,
            )

        self.assertTrue(is_new)
        self.assertFalse(sent)
        notify.assert_not_awaited()
        added = db.add.call_args[0][0]
        self.assertFalse(added.is_new)
        self.assertEqual(search.new_count, 0)


if __name__ == "__main__":
    unittest.main()
