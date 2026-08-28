"""Нормалізація регіонів для всіх областей і джерел пошуку."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from app.schemas.schemas import SearchFilters
from app.services.auto_ria.constants import REGION_TO_STATE_CITY
from app.services.auto_ria.mapper import filters_to_search_params
from app.services.olx.constants import REGION_TO_OLX_REGION_ID
from app.services.olx.mapper import filters_to_olx_params
from app.services.search.filter_multi import canonicalize_region, sync_multi_search_filters
from app.services.search.region_voice import CANONICAL_UA_REGIONS

OBLASTS = [r for r in CANONICAL_UA_REGIONS if r.endswith(" область")]


class RegionCanonicalizeAllOblastsTests(unittest.TestCase):
    def test_short_form_without_oblast_word(self):
        for region in OBLASTS:
            short = region.replace(" область", "")
            with self.subTest(region=region):
                self.assertEqual(canonicalize_region(short), region)
                synced = sync_multi_search_filters(SearchFilters(brand="BMW", region=short))
                self.assertEqual(synced.region, region)
                self.assertEqual(synced.regions, [region])

    def test_schema_validator_normalizes_short_region(self):
        filters = SearchFilters(brand="Zeekr", model="001", region="Хмельницька")
        self.assertEqual(filters.region, "Хмельницька область")

    def test_auto_ria_state_for_every_oblast_short_and_full(self):
        for region in OBLASTS:
            if region == "Луганська область":
                continue  # немає в /auto/states
            short = region.replace(" область", "")
            with self.subTest(region=region):
                full_key = region.lower()
                short_key = short.lower()
                self.assertIn(full_key, REGION_TO_STATE_CITY)
                self.assertIn(short_key, REGION_TO_STATE_CITY)
                self.assertEqual(
                    REGION_TO_STATE_CITY[full_key],
                    REGION_TO_STATE_CITY[short_key],
                )

    def test_auto_ria_mapper_short_regions(self):
        async def run():
            from app.services.auto_ria import catalog as ar_catalog

            ar_catalog._marks_cache = None
            ar_catalog._models_cache.clear()
            client = AsyncMock()
            client.get_marks = AsyncMock(return_value=[{"name": "BMW", "value": 9}])
            client.get_models = AsyncMock(return_value=[{"name": "X5", "value": 1}])
            for region in OBLASTS:
                if region == "Луганська область":
                    continue
                short = region.replace(" область", "")
                ar_catalog._marks_cache = None
                ar_catalog._models_cache.clear()
                params = await filters_to_search_params(
                    client,
                    SearchFilters(brand="BMW", model="X5", region=short),
                    page=1,
                    per_page=20,
                )
                expected = REGION_TO_STATE_CITY[region.lower()][0]
                self.assertEqual(params.get("state[0]"), expected, short)

        import asyncio

        asyncio.run(run())

    def test_olx_mapper_short_regions(self):
        for region in OBLASTS:
            if region in ("Луганська область", "Київська область"):
                # Київська без «область» у UI часто = м. Київ на OLX; повна назва має region_id.
                continue
            short = region.replace(" область", "")
            with self.subTest(region=region):
                params = filters_to_olx_params(SearchFilters(brand="Toyota", region=short))
                expected = REGION_TO_OLX_REGION_ID.get(region.lower())
                self.assertEqual(params.region_id, expected, short)
                self.assertEqual(params.region_label, region)

        kyiv_oblast = filters_to_olx_params(
            SearchFilters(brand="Toyota", region="Київська область")
        )
        self.assertEqual(kyiv_oblast.region_id, 25)

    def test_numeric_model_still_not_omni_id_for_all_regions(self):
        async def run():
            from app.services.auto_ria import catalog as ar_catalog

            client = AsyncMock()
            client.get_marks = AsyncMock(return_value=[{"name": "Zeekr", "value": 55280}])
            client.get_models = AsyncMock(return_value=[{"name": "001", "value": 64237}])
            for region in ("Одеська", "Львівська", "Хмельницька", "Київська область"):
                ar_catalog._marks_cache = None
                ar_catalog._models_cache.clear()
                params = await filters_to_search_params(
                    client,
                    SearchFilters(brand="Zeekr", model="001", region=region),
                    page=1,
                    per_page=20,
                )
                self.assertNotIn("omni_id", params, region)
                self.assertEqual(params.get("marka_id[0]"), 55280, region)
                self.assertEqual(params.get("model_id[0]"), 64237, region)
                self.assertIn("state[0]", params, region)

        import asyncio

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
