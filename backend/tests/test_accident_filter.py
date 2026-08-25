"""Тести фільтра ДТП для різних джерел."""

from __future__ import annotations

import unittest

from app.schemas.schemas import ListingOut, SearchFilters
from app.services.listings.accident import (
    extract_listing_accident_had,
    listing_matches_accident_filter,
)
from app.services.search.advanced_filters import listing_matches_advanced_filters


def _item(**kwargs) -> ListingOut:
    base = {
        "id": "test_1",
        "source": "imperiya",
        "title": "Test Car",
        "brand": "Toyota",
        "model": "Camry",
        "year": 2020,
        "price": 10000,
        "currency": "USD",
        "mileage": 50000,
        "fuel": "Бензин",
        "transmission": "Автомат",
        "region": "Київ",
        "description": None,
        "images": [],
        "url": "https://example.test",
        "seller_type": "private",
        "price_history": [],
        "is_duplicate": False,
        "published_at": "2026-01-01T00:00:00+02:00",
        "found_at": "2026-01-01T00:00:00+02:00",
    }
    base.update(kwargs)
    return ListingOut(**base)


class AccidentExtractTests(unittest.TestCase):
    def test_imperiya_was_accident_true(self):
        item = _item(source_data={"imperiya": {"wasAccident": True}})
        self.assertTrue(extract_listing_accident_had(item))

    def test_imperiya_was_accident_false(self):
        item = _item(source_data={"imperiya": {"wasAccident": False}})
        self.assertFalse(extract_listing_accident_had(item))

    def test_text_fallback_had(self):
        item = _item(description="Після ДТП, потребує ремонту")
        self.assertTrue(extract_listing_accident_had(item))

    def test_imperiya_condition_was_accident(self):
        item = _item(
            source_data={
                "imperiya": {
                    "condition": {"wasAccident": False, "technicalState": "Справний"},
                }
            }
        )
        self.assertFalse(extract_listing_accident_had(item))

    def test_reono_text_none_compact(self):
        item = _item(source="reono", description="Автомобіль в хорошому стані. В ДТП небув.")
        self.assertFalse(extract_listing_accident_had(item))


class AccidentFilterTests(unittest.TestCase):
    def test_auto_ria_trusts_api_filter(self):
        item = _item(source="auto_ria", source_data={"autoData": {}})
        self.assertTrue(listing_matches_accident_filter(item, "had"))
        self.assertTrue(listing_matches_accident_filter(item, "none"))

    def test_imperiya_had_requires_flag(self):
        ok = _item(source_data={"imperiya": {"wasAccident": True}})
        bad = _item(source_data={"imperiya": {"wasAccident": False}})
        self.assertTrue(listing_matches_accident_filter(ok, "had"))
        self.assertFalse(listing_matches_accident_filter(bad, "had"))

    def test_imperiya_none_rejects_accident(self):
        bad = _item(source_data={"imperiya": {"wasAccident": True}})
        ok = _item(source_data={"imperiya": {"wasAccident": False}})
        self.assertFalse(listing_matches_accident_filter(bad, "none"))
        self.assertTrue(listing_matches_accident_filter(ok, "none"))

    def test_advanced_filter_uses_imperiya_flag(self):
        item = _item(source_data={"imperiya": {"wasAccident": True}})
        self.assertFalse(
            listing_matches_advanced_filters(item, SearchFilters(accident="none"))
        )
        self.assertTrue(
            listing_matches_advanced_filters(item, SearchFilters(accident="had"))
        )

    def test_advanced_filter_auto_ria_not_rejected_without_damage_field(self):
        item = _item(source="auto_ria", source_data={"autoData": {}})
        self.assertTrue(
            listing_matches_advanced_filters(item, SearchFilters(accident="had"))
        )


if __name__ == "__main__":
    unittest.main()
