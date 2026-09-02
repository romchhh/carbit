"""API-прапорці had_accident / usa_import на ListingOut."""

from __future__ import annotations

import unittest
from datetime import datetime

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import ListingOut
from app.services.olx.mapper import olx_listing_to_listing_out
from app.services.olx.parser import OlxListing


def _base_listing(**overrides) -> dict:
    data = {
        "id": "test_1",
        "source": "olx",
        "title": "BMW X5",
        "brand": "BMW",
        "model": "X5",
        "year": 2020,
        "price": 10000,
        "currency": "USD",
        "mileage": 50000,
        "fuel": "Бензин",
        "transmission": "Автомат",
        "region": "Київ",
        "description": None,
        "images": [],
        "url": "https://example.com",
        "seller_type": "private",
        "source_data": {},
        "price_history": [],
        "is_duplicate": False,
        "published_at": datetime(2026, 1, 1, tzinfo=KYIV_TZ),
        "found_at": datetime(2026, 1, 1, tzinfo=KYIV_TZ),
    }
    data.update(overrides)
    return data


class ListingOutFlagsTests(unittest.TestCase):
    def test_olx_usa_spec_sets_usa_import(self):
        listing = OlxListing(
            listing_id="1",
            title="Ford Mustang",
            url="https://www.olx.ua/d/uk/obyavlenie/test-ID1.html",
            specs={"Авто пригнано з": "США"},
        )
        out = olx_listing_to_listing_out(listing)
        self.assertTrue(out.usa_import)

    def test_olx_accident_spec_sets_had_accident(self):
        listing = OlxListing(
            listing_id="2",
            title="Audi A4",
            url="https://www.olx.ua/d/uk/obyavlenie/test-ID2.html",
            specs={"Стан": "Після ДТП"},
        )
        out = olx_listing_to_listing_out(listing)
        self.assertTrue(out.had_accident)

    def test_auto_ria_damage_id(self):
        out = ListingOut(
            **_base_listing(
                id="auto_ria_1",
                source="auto_ria",
                source_data={"autoData": {"damageId": 2}},
            )
        )
        self.assertTrue(out.had_accident)

    def test_imperiya_was_accident(self):
        out = ListingOut(
            **_base_listing(
                id="imperiya_1",
                source="imperiya",
                source_data={"imperiya": {"wasAccident": False}},
            )
        )
        self.assertFalse(out.had_accident)


if __name__ == "__main__":
    unittest.main()
