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
        item = _item(mileage=200, title="Audi A4", year=2024)
        self.assertTrue(listing_matches_category(item, "new"))
        self.assertFalse(listing_matches_category(item, "used"))

    def test_new_rejects_before_2020(self):
        item = _item(mileage=200, title="Audi A4 з салону", year=2019)
        self.assertFalse(listing_matches_category(item, "new"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_new_rejects_high_mileage_even_with_novyi_word(self):
        item = _item(mileage=90000, title="BMW 320 як новий")
        self.assertFalse(listing_matches_category(item, "new"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_new_rejects_unknown_mileage_without_markers(self):
        item = _item(mileage=0, title="Toyota Camry 2018")
        self.assertFalse(listing_matches_category(item, "new"))

    def test_new_zero_mileage_with_salon_marker(self):
        item = _item(mileage=0, title="Toyota Camry з салону", year=2024)
        self.assertTrue(listing_matches_category(item, "new"))
        self.assertFalse(listing_matches_category(item, "used"))

    def test_new_auto_ria_catalog_id_counts_as_new(self):
        item = _item(id="new_auto_ria_555", title="BMW X5", mileage=0, year=2025)
        self.assertTrue(listing_matches_category(item, "new"))
        self.assertFalse(listing_matches_category(item, "used"))

    def test_new_auto_ria_catalog_rejects_before_2020(self):
        item = _item(id="new_auto_ria_555", title="BMW X5", mileage=0, year=2018)
        self.assertFalse(listing_matches_category(item, "new"))
        self.assertTrue(listing_matches_category(item, "used"))

    def test_udrive_always_counts_as_new(self):
        item = _item(id="udrive_abc", source="udrive", title="Audi A5", mileage=0, year=2024)
        self.assertTrue(listing_matches_category(item, "all"))
        self.assertTrue(listing_matches_category(item, "new"))
        self.assertFalse(listing_matches_category(item, "used"))
        self.assertFalse(listing_matches_category(item, "import"))

    def test_udrive_new_even_with_nonzero_mileage(self):
        item = _item(id="udrive_abc", source="udrive", title="Audi A5", mileage=50, year=2025)
        self.assertTrue(listing_matches_category(item, "new"))
        self.assertFalse(listing_matches_category(item, "used"))

    def test_udrive_rejects_before_2020(self):
        item = _item(id="udrive_abc", source="udrive", title="Audi A5", mileage=0, year=2019)
        self.assertFalse(listing_matches_category(item, "new"))
        self.assertTrue(listing_matches_category(item, "used"))

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
        self.assertEqual(new.get("s_yers[0]"), 2020)

        imp = await fake_params("import")
        self.assertEqual(imp.get("custom"), 1)


class AutoRiaNewSearchEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_category_uses_new_search_endpoint(self):
        from app.services.auto_ria.service import _search_auto_ria_body, collect_auto_ria_ids

        mock_info = {
            "autoId": 555,
            "markName": "BMW",
            "modelName": "X5",
            "title": "BMW X5",
            "year": 2025,
            "USD": 80000,
            "linkToView": "/newauto/555.html",
            "photo": "https://cdn/new.jpg",
        }

        with patch("app.services.auto_ria.service.AutoRiaClient") as client_cls:
            client = client_cls.return_value
            client.search = AsyncMock()
            client.search_new = AsyncMock(return_value={"count": 1, "ids": [555]})
            client.get_new_info = AsyncMock(return_value=mock_info)
            client.get_info = AsyncMock()
            with patch(
                "app.services.auto_ria.service.filters_to_search_params",
                new_callable=AsyncMock,
                return_value={"marka_id[0]": 9},
            ), patch(
                "app.services.auto_ria.service.new_info_to_listing",
                return_value=_item(id="new_auto_ria_555", title="BMW X5", mileage=0, year=2025),
            ):
                body = await _search_auto_ria_body(
                    SearchFilters(category="new", brand="BMW"),
                    page=1,
                    per_page=10,
                )
                ids, total = await collect_auto_ria_ids(
                    SearchFilters(category="new", brand="BMW"),
                    max_ids=20,
                )

        client.search.assert_not_called()
        client.get_info.assert_not_called()
        client.search_new.assert_called()
        client.get_new_info.assert_called()
        self.assertEqual(total, 1)
        self.assertTrue(all(aid.startswith("n:") for aid in ids))
        self.assertEqual(len(body.items), 1)
        self.assertTrue(body.items[0].id.startswith("new_auto_ria_"))

    async def test_new_search_reads_legacy_autos_key(self):
        from app.services.auto_ria.service import _search_auto_ria_body

        with patch("app.services.auto_ria.service.AutoRiaClient") as client_cls:
            client = client_cls.return_value
            client.search = AsyncMock()
            client.search_new = AsyncMock(return_value={"count": 1, "autos": [777]})
            client.get_new_info = AsyncMock(return_value={"autoId": 777})
            with patch(
                "app.services.auto_ria.service.filters_to_search_params",
                new_callable=AsyncMock,
                return_value={"marka_id[0]": 9},
            ), patch(
                "app.services.auto_ria.service.new_info_to_listing",
                return_value=_item(
                    id="new_auto_ria_777",
                    title="BMW 5 Series",
                    model="5 Series",
                    mileage=0,
                    year=2025,
                ),
            ):
                body = await _search_auto_ria_body(
                    SearchFilters(category="new", brand="BMW", model="5 Series"),
                    page=1,
                    per_page=10,
                )
        client.get_new_info.assert_called()
        self.assertEqual(len(body.items), 1)


class NewSearchIdsParseTests(unittest.TestCase):
    def test_prefers_ids_over_autos(self):
        from app.services.auto_ria.service import _new_search_ids

        self.assertEqual(_new_search_ids({"ids": [1, 2], "autos": [9]}), ["1", "2"])
        self.assertEqual(_new_search_ids({"autos": [9, 8]}), ["9", "8"])
        self.assertEqual(_new_search_ids({"count": 3}), [])


if __name__ == "__main__":
    unittest.main()
