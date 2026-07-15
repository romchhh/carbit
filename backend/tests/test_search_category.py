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

    def test_new_by_mileage(self):
        item = _item(mileage=200, title="Audi A4")
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

        async def fake_params(category: str, **filter_kw):
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
                    SearchFilters(category=category, **filter_kw),
                    page=1,
                    per_page=20,
                )

        used = await fake_params("used")
        self.assertEqual(used.get("searchType"), 4)
        self.assertEqual(used.get("custom"), 0)

        new = await fake_params("new")
        self.assertEqual(new.get("searchType"), 1)
        self.assertEqual(new.get("raceTo"), 15)

        # Категорія «нові» перебиває user mileage_to (до 15 тис. км).
        new_with_mileage = await fake_params("new", mileage_to=50000)
        self.assertEqual(new_with_mileage.get("raceTo"), 15)

        imp = await fake_params("import")
        self.assertEqual(imp.get("custom"), 1)

        all_cat = await fake_params("all")
        self.assertEqual(all_cat.get("searchType"), 4)
        self.assertNotIn("raceTo", all_cat)


class ZeroKmMarkerTests(unittest.TestCase):
    def test_nearly_new_by_mileage_is_new(self):
        item = _item(
            mileage=9300,
            description="Авто з пробігом 9300 км, знаходиться у Вінниці",
        )
        self.assertTrue(listing_matches_category(item, "new"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_high_mileage_9300_substring_not_new(self):
        # «9300 км» у тексті не має давати false «0 км», якщо пробіг великий.
        item = _item(
            mileage=50000,
            description="раніше було 9300 км, зараз більше",
        )
        self.assertFalse(listing_matches_category(item, "new"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_true_zero_km_is_new(self):
        item = _item(mileage=0, description="Без пробігу, 0 км з салону")
        self.assertTrue(listing_matches_category(item, "new"))


class NewMarkerFalsePositiveTests(unittest.TestCase):
    def test_innovatsiynyi_is_not_new(self):
        item = _item(mileage=50000, description="інноваційний підхід до сервісу")
        self.assertFalse(listing_matches_category(item, "new"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_nova_rezyna_high_mileage_not_new(self):
        item = _item(mileage=60000, description="нова резина комплект")
        self.assertFalse(listing_matches_category(item, "new"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_yak_z_salonu_high_mileage_not_new(self):
        item = _item(mileage=80000, description="стан як з салону")
        self.assertFalse(listing_matches_category(item, "new"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_nove_avto_phrase_is_new(self):
        item = _item(mileage=18000, description="продаж, нове авто з документами")
        self.assertTrue(listing_matches_category(item, "new"))

    def test_china_origin_low_mileage_still_new(self):
        item = _item(
            mileage=9000,
            description="Zeekr 001, розмитнений, привезений з Китаю",
        )
        self.assertTrue(listing_matches_category(item, "new"))
        self.assertFalse(listing_matches_category(item, "import"))


class ImportMarkerFalsePositiveTests(unittest.TestCase):
    def test_parts_from_china_not_import(self):
        item = _item(description="запчастини з Китаю в наявності", mileage=50000)
        self.assertFalse(listing_matches_category(item, "import"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_cleared_from_eu_is_used(self):
        item = _item(description="машина з ЄС, уже розмитнена", mileage=70000)
        self.assertFalse(listing_matches_category(item, "import"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_poland_delivery_header_not_import(self):
        item = _item(description="Польща. Доставка по Україні", mileage=90000)
        self.assertFalse(listing_matches_category(item, "import"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_disks_on_order_not_import(self):
        item = _item(description="диски під замовлення", mileage=40000)
        self.assertFalse(listing_matches_category(item, "import"))

    def test_real_import_still_matches(self):
        item = _item(description="авто під пригон з США, нерозмитнене", mileage=40000)
        self.assertTrue(listing_matches_category(item, "import"))
        self.assertFalse(listing_matches_category(item, "used"))

    def test_evronomer_uncleared_is_import(self):
        item = _item(description="на єврономерах, без розмитнення", mileage=50000)
        self.assertTrue(listing_matches_category(item, "import"))


if __name__ == "__main__":
    unittest.main()
