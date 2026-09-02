"""AUTO.RIA: Zeekr URL, omni_id, регіон з stateId."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.schemas.schemas import ListingOut, SearchFilters
from app.services.auto_ria.mapper import _region_from_auto_ria_info, filters_to_search_params
from app.services.auto_ria.url_parse import listing_id_matches_omni_search, omni_id_from_search_filters
from app.services.telegram_channels.mapper import listing_out_matches_filters


class AutoRiaZeekrSearchTests(unittest.TestCase):
    def test_omni_id_from_zeekr_url_in_brand(self):
        filters = SearchFilters(
            brand="https://auto.ria.com/uk/auto_zeekr_001_40351832.html",
            model="001",
        )
        self.assertEqual(omni_id_from_search_filters(filters), "40351832")

    def test_url_in_brand_passes_post_filter_for_target_listing(self):
        from app.core.timezone import now_kyiv

        url = "https://auto.ria.com/uk/auto_zeekr_001_40351832.html"
        filters = SearchFilters(brand=url)
        listing = ListingOut(
            id="auto_ria_40351832",
            source="auto_ria",
            title="Zeekr 001",
            brand="Zeekr",
            model="001",
            year=2024,
            price=42000,
            currency="USD",
            mileage=16000,
            fuel="електро",
            transmission="автомат",
            region="Хмельницький, Хмельницька",
            description=None,
            images=[],
            url=url,
            seller_type="dealer",
            price_history=[],
            is_duplicate=False,
            published_at=now_kyiv(),
            found_at=now_kyiv(),
        )
        self.assertTrue(listing_id_matches_omni_search(listing.id, filters))
        self.assertTrue(listing_out_matches_filters(listing, filters))

    def test_region_from_state_id_when_names_missing(self):
        region = _region_from_auto_ria_info(
            {},
            {"stateId": 12},
            {},
        )
        self.assertEqual(region, "одеська область")

    def test_region_from_state_id_khmelnytskyi(self):
        region = _region_from_auto_ria_info(
            {},
            {"stateId": 4},
            {},
        )
        self.assertEqual(region, "хмельницька область")

    def test_zeekr_with_kyiv_region_not_dropped_on_generic_ukraine(self):
        from app.core.timezone import now_kyiv

        listing = ListingOut(
            id="auto_ria_40351832",
            source="auto_ria",
            title="Zeekr 001",
            brand="Zeekr",
            model="001",
            year=2024,
            price=42999,
            currency="USD",
            mileage=0,
            fuel="електро",
            transmission="автомат",
            region="Україна",
            description=None,
            images=[],
            url="https://auto.ria.com/uk/auto_zeekr_001_40351832.html",
            seller_type="dealer",
            price_history=[],
            is_duplicate=False,
            published_at=now_kyiv(),
            found_at=now_kyiv(),
        )
        filters = SearchFilters(brand="Zeekr", model="001", region="Одеська область")
        self.assertTrue(listing_out_matches_filters(listing, filters))

    def test_filters_to_search_params_omni_id_short_circuit(self):
        async def run():
            client = AsyncMock()
            filters = SearchFilters(brand="https://auto.ria.com/uk/auto_zeekr_001_40349889.html")
            params = await filters_to_search_params(client, filters, page=1, per_page=20)
            self.assertEqual(params.get("omni_id"), "40349889")
            self.assertNotIn("marka_id[0]", params)
            client.get_marks.assert_not_called()

        import asyncio

        asyncio.run(run())

    def test_filters_to_search_params_zeekr_001_khmelnytskyi(self):
        async def run():
            client = AsyncMock()
            client.get_marks = AsyncMock(
                return_value=[{"name": "Zeekr", "value": 55280}],
            )
            client.get_models = AsyncMock(
                return_value=[{"name": "001", "value": 64237}],
            )
            filters = SearchFilters(
                brand="Zeekr",
                model="001",
                region="Хмельницька",
                not_customs="hide",
            )
            from app.services.auto_ria import catalog as ar_catalog

            ar_catalog._marks_cache = None
            ar_catalog._models_cache.clear()
            params = await filters_to_search_params(client, filters, page=1, per_page=20)
            self.assertNotIn("omni_id", params)
            self.assertEqual(params.get("marka_id[0]"), 55280)
            self.assertEqual(params.get("model_id[0]"), 64237)
            self.assertEqual(params.get("state[0]"), 4)
            self.assertEqual(params.get("custom"), 0)

        import asyncio

        asyncio.run(run())


    def test_filters_to_search_params_regions_array_only(self):
        async def run():
            client = AsyncMock()
            client.get_marks = AsyncMock(
                return_value=[{"name": "Zeekr", "value": 55280}],
            )
            client.get_models = AsyncMock(
                return_value=[{"name": "001", "value": 64237}],
            )
            filters = SearchFilters(
                brands=["Zeekr"],
                models=["001"],
                regions=["Хмельницька"],
            )
            from app.services.auto_ria import catalog as ar_catalog

            ar_catalog._marks_cache = None
            ar_catalog._models_cache.clear()
            params = await filters_to_search_params(client, filters, page=1, per_page=20)
            self.assertNotIn("omni_id", params)
            self.assertEqual(params.get("marka_id[0]"), 55280)
            self.assertEqual(params.get("model_id[0]"), 64237)
            self.assertEqual(params.get("state[0]"), 4)

        import asyncio

        asyncio.run(run())

    def test_numeric_models_never_omni_in_api_params(self):
        cases = [
            ("Zeekr", "001", 55280, 64237),
            ("Porsche", "911", 59, 539),
            ("Mazda", "3", 47, 1692),
        ]

        async def run():
            from app.services.auto_ria import catalog as ar_catalog

            client = AsyncMock()
            for brand, model, mark_id, model_id in cases:
                with self.subTest(brand=brand, model=model):
                    client.get_marks = AsyncMock(return_value=[{"name": brand, "value": mark_id}])
                    client.get_models = AsyncMock(return_value=[{"name": model, "value": model_id}])
                    ar_catalog._marks_cache = None
                    ar_catalog._models_cache.clear()
                    params = await filters_to_search_params(
                        client,
                        SearchFilters(brand=brand, model=model),
                        page=1,
                        per_page=20,
                    )
                    self.assertNotIn("omni_id", params)
                    self.assertEqual(params.get("marka_id[0]"), mark_id)
                    self.assertEqual(params.get("model_id[0]"), model_id)

        import asyncio

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
