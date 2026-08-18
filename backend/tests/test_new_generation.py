"""New-car generation aliases (Audi A4→A5, Mercedes C-Class→CLE) and Cyrillic С-клас."""

from __future__ import annotations

import datetime as dt
import unittest

from app.schemas.schemas import ListingOut, SearchFilters
from app.services.search.new_generation import new_generation_models
from app.services.telegram_channels.mapper import listing_out_matches_filters


def _item(**kwargs) -> ListingOut:
    now = dt.datetime.now(dt.timezone.utc)
    base = dict(
        id="auto_ria_1",
        source="auto_ria",
        title="Audi A4",
        brand="Audi",
        model="A4",
        year=2024,
        price=40000,
        currency="USD",
        mileage=0,
        region="Київ",
        url="https://example.com",
        images=[],
        description=None,
        published_at=now,
        found_at=now,
        price_history=[],
        is_duplicate=False,
        fuel="Бензин",
        transmission="Автомат",
        seller_type="dealer",
    )
    base.update(kwargs)
    return ListingOut(**base)


class NewGenerationAliasTests(unittest.TestCase):
    def test_audi_a4_expands_to_a5(self):
        names = new_generation_models("Audi", "A4")
        self.assertIn("A4", names)
        self.assertIn("A5", names)

    def test_cyrillic_c_class_expands_like_latin(self):
        latin = new_generation_models("Mercedes-Benz", "C-Class")
        cyr = new_generation_models("Mercedes-Benz", "С-клас")
        self.assertEqual(latin, cyr)
        self.assertIn("CLE-Class", latin)

    def test_unmapped_model_stays_itself(self):
        self.assertEqual(new_generation_models("BMW", "X5"), ("X5",))

    def test_new_a5_matches_a4_filter(self):
        item = _item(
            id="new_auto_ria_1",
            title="Audi A5",
            brand="Audi",
            model="A5",
            year=2025,
        )
        self.assertTrue(
            listing_out_matches_filters(
                item, SearchFilters(category="new", brand="Audi", model="A4")
            )
        )

    def test_used_a5_does_not_match_a4_filter(self):
        item = _item(
            id="auto_ria_1",
            title="Audi A5",
            brand="Audi",
            model="A5",
            year=2021,
            mileage=40000,
        )
        self.assertFalse(
            listing_out_matches_filters(
                item, SearchFilters(category="used", brand="Audi", model="A4")
            )
        )

    def test_new_cle_matches_c_class_filter(self):
        item = _item(
            id="new_auto_ria_2",
            title="Mercedes-Benz CLE-Class",
            brand="Mercedes-Benz",
            model="CLE-Class",
            year=2026,
            mileage=0,
        )
        self.assertTrue(
            listing_out_matches_filters(
                item,
                SearchFilters(category="new", brand="Mercedes-Benz", model="C-Class"),
            )
        )

    def test_cyrillic_c_class_filter_matches_latin_title(self):
        item = _item(
            id="new_auto_ria_3",
            title="Mercedes-Benz C-Class",
            brand="Mercedes-Benz",
            model="C-Class",
            year=2026,
            mileage=0,
        )
        self.assertTrue(
            listing_out_matches_filters(
                item,
                SearchFilters(category="new", brand="Mercedes-Benz", model="С-клас"),
            )
        )


if __name__ == "__main__":
    unittest.main()
