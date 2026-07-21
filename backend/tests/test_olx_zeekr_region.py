"""OLX: Zeekr 001 + регіон (Boyarka / Одеса)."""

from __future__ import annotations

import unittest

from app.schemas.schemas import SearchFilters
from app.services.olx.mapper import filters_to_olx_params
from app.services.olx.parser import OlxListing, passes_olx_filters
from app.services.olx.service import _text_query_variants_for_filters
from app.services.search.region_match import listing_region_matches_filter


class OlxZeekrRegionTests(unittest.TestCase):
    def test_zeekr001_title_passes_post_filter(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Zeekr", model="001", currency="UAH")
        )
        listing = OlxListing(
            title="Продам Zeekr001",
            price="1343492",
            currency="UAH",
            city="Одеса",
        )
        self.assertTrue(passes_olx_filters(listing, params))

    def test_kyiv_oblast_includes_boyarka(self):
        params = filters_to_olx_params(
            SearchFilters(
                brand="Zeekr",
                model="001",
                currency="UAH",
                region="Київська область",
            )
        )
        self.assertEqual(params.region_label, "Київська область")
        listing = OlxListing(
            title="Zeekr 001 WE 2025",
            price="20000",
            currency="USD",
            city="Боярка",
            raw_params={
                "location": {
                    "cityName": "Боярка",
                    "regionName": "Київська область",
                    "pathName": "Київська область, Боярка",
                }
            },
        )
        self.assertTrue(passes_olx_filters(listing, params))

    def test_odessa_region(self):
        self.assertTrue(
            listing_region_matches_filter("Одеса, Пересипський", "Одеська область")
        )

    def test_text_query_variants_include_brand_only(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Zeekr", model="001", currency="UAH")
        )
        variants = _text_query_variants_for_filters(
            SearchFilters(brand="Zeekr", model="001", currency="UAH"),
            params,
        )
        self.assertIn("zeekr 001", variants)
        self.assertIn("zeekr", variants)


if __name__ == "__main__":
    unittest.main()
