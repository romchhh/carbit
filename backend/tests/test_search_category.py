"""Тести категорій пошуку (вживані / нові / під пригон)."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.search.category import listing_matches_category


def _item(**kwargs) -> ListingOut:
    base = dict(
        id="a1",
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


class CategoryMatchTests(unittest.TestCase):
    def test_import(self):
        item = _item(title="Tesla Model 3 під пригон", mileage=40000)
        self.assertTrue(listing_matches_category(item, "import"))
        self.assertFalse(listing_matches_category(item, "used"))

    def test_import_europe_phrase(self):
        desc = """Ford Focus - 2014
Пригнано з Європи 🇪🇺
🛣 Пробіг: 210 тис. км"""
        item = _item(title="Ford Focus 2014", description=desc, mileage=210000)
        self.assertTrue(listing_matches_category(item, "import"))
        self.assertFalse(listing_matches_category(item, "used"))

    def test_new_by_mileage(self):
        item = _item(mileage=200, title="Audi A4")
        self.assertTrue(listing_matches_category(item, "new"))
        self.assertFalse(listing_matches_category(item, "used"))

    def test_new_rejects_high_mileage_even_with_novyi_word(self):
        item = _item(mileage=90000, title="BMW 320 як новий")
        self.assertFalse(listing_matches_category(item, "new"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_new_rejects_unknown_mileage_without_markers(self):
        item = _item(mileage=0, title="Toyota Camry 2018")
        self.assertFalse(listing_matches_category(item, "new"))

    def test_new_zero_mileage_with_salon_marker(self):
        item = _item(mileage=0, title="Toyota Camry з салону")
        self.assertTrue(listing_matches_category(item, "new"))
        self.assertFalse(listing_matches_category(item, "used"))

    def test_used(self):
        item = _item(mileage=90000)
        self.assertTrue(listing_matches_category(item, "used"))
        self.assertFalse(listing_matches_category(item, "new"))
        self.assertFalse(listing_matches_category(item, "import"))


class AutoRiaCategoryParamsTests(unittest.IsolatedAsyncioTestCase):
    async def test_maps_category_params(self):
        from app.services.auto_ria.mapper import filters_to_search_params

        client = object()

        async def fake_params(category: str):
            with (
                patch(
                    "app.services.auto_ria.mapper.resolve_mark_id",
                    AsyncMock(return_value=None),
                ),
                patch(
                    "app.services.auto_ria.mapper.resolve_model_id",
                    AsyncMock(return_value=None),
                ),
            ):
                return await filters_to_search_params(
                    client,  # type: ignore[arg-type]
                    SearchFilters(category=category),
                    page=1,
                    per_page=20,
                )

        used = await fake_params("used")
        self.assertEqual(used.get("searchType"), 4)
        self.assertEqual(used.get("custom"), 0)

        new = await fake_params("new")
        self.assertEqual(new.get("searchType"), 1)
        self.assertEqual(new.get("raceTo"), 1)

        imp = await fake_params("import")
        self.assertEqual(imp.get("custom"), 1)


if __name__ == "__main__":
    unittest.main()
