from __future__ import annotations

import unittest
from datetime import datetime

from app.core.timezone import KYIV_TZ, format_time_ago, now_kyiv
from app.schemas.schemas import ListingOut, PaginatedListings
from app.services.listings.sanitize import sanitize_listing_out
from app.services.listings.sort_dates import coalesce_listing_published_at


def _listing(**overrides) -> ListingOut:
    base = dict(
        id="auto_ria_1",
        source="auto_ria",
        title="Test car",
        brand="Test",
        model="Car",
        year=2007,
        price=9700,
        currency="USD",
        mileage=240_000,
        fuel="Газ",
        transmission="Механіка",
        region="Миколаїв",
        description=None,
        images=[],
        url="https://example.com/x",
        seller_type="private",
        source_data={},
        price_history=[],
        is_duplicate=False,
        published_at=datetime(1970, 1, 1, tzinfo=KYIV_TZ),
        found_at=datetime(2026, 4, 20, 14, 0, tzinfo=KYIV_TZ),
    )
    base.update(overrides)
    return ListingOut.model_construct(**base)


class PublishedAtCoalesceTests(unittest.TestCase):
    def test_coalesce_replaces_epoch_placeholder(self):
        found = datetime(2026, 4, 20, 14, 0, tzinfo=KYIV_TZ)
        resolved = coalesce_listing_published_at(
            datetime(1970, 1, 1, 12, 0, tzinfo=KYIV_TZ),
            found_at=found,
        )
        self.assertEqual(resolved, found)

    def test_coalesce_keeps_real_published_at(self):
        published = datetime(2026, 3, 1, 10, 0, tzinfo=KYIV_TZ)
        found = datetime(2026, 4, 20, 14, 0, tzinfo=KYIV_TZ)
        resolved = coalesce_listing_published_at(published, found_at=found)
        self.assertEqual(resolved, published)

    def test_sanitize_replaces_epoch_placeholder(self):
        item = sanitize_listing_out(_listing())
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.published_at.year, 2026)
        self.assertEqual(item.published_at.month, 4)
        self.assertEqual(item.published_at.day, 20)

    def test_format_time_ago_hides_epoch(self):
        self.assertIsNone(format_time_ago(datetime(1970, 1, 1, tzinfo=KYIV_TZ)))
        self.assertIsNotNone(format_time_ago(now_kyiv()))


if __name__ == "__main__":
    unittest.main()
