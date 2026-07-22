"""Фільтр кількості місць (розширений пошук)."""

from __future__ import annotations

import unittest
from datetime import datetime

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.search.advanced_filters import (
    extract_listing_seats,
    listing_matches_advanced_filters,
    listing_matches_seats_filter,
)
from app.services.telegram_channels.mapper import listing_out_matches_filters


def _item(**kwargs) -> ListingOut:
    base = dict(
        id="auto_ria_1",
        source="auto_ria",
        title="VW Multivan",
        brand="Volkswagen",
        model="Multivan",
        year=2018,
        price=25000,
        currency="USD",
        mileage=120000,
        fuel="Дизель",
        transmission="Автомат",
        region="Київ",
        description=None,
        images=[],
        url="https://example.com",
        seller_type="private",
        vin=None,
        source_data={"autoData": {"seats": 7}},
        price_history=[],
        is_duplicate=False,
        published_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
        found_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
    )
    base.update(kwargs)
    return ListingOut(**base)


class AdvancedSeatsTests(unittest.TestCase):
    def test_extract_from_auto_ria(self):
        self.assertEqual(extract_listing_seats(_item()), 7)

    def test_extract_from_text(self):
        item = _item(
            source="telegram",
            source_data=None,
            description="🚘 Toyota\n7 місць в салоні",
        )
        self.assertEqual(extract_listing_seats(item), 7)

    def test_seats_range(self):
        item = _item()
        filters = SearchFilters(seats_from=5, seats_to=7)
        self.assertTrue(listing_matches_seats_filter(item, filters))
        self.assertFalse(
            listing_matches_seats_filter(item, SearchFilters(seats_from=8, seats_to=9))
        )

    def test_listing_out_matches(self):
        item = _item()
        self.assertTrue(
            listing_out_matches_filters(item, SearchFilters(seats_from=7, seats_to=7))
        )
        self.assertFalse(
            listing_out_matches_filters(item, SearchFilters(seats_from=5, seats_to=5))
        )

    def test_unknown_seats_passes_when_not_in_listing(self):
        item = _item(source_data={})
        self.assertTrue(listing_matches_advanced_filters(item, SearchFilters(seats_from=5)))


if __name__ == "__main__":
    unittest.main()
