"""OLX: марки без taxonomy path → text query."""

from __future__ import annotations

import unittest

from app.schemas.schemas import SearchFilters
from app.services.olx.brand_slugs import brand_uses_olx_text_search
from app.services.olx.mapper import filters_to_olx_params
from app.services.olx.parser import OlxListing, build_search_url, passes_olx_filters


class OlxTextSearchBrandTests(unittest.TestCase):
    def test_known_404_brands_use_text(self):
        for brand in (
            "Zeekr",
            "Haval",
            "Genesis",
            "Cupra",
            "Jaecoo",
            "Omoda",
            "XPeng",
            "NIO",
            "Li Auto",
            "Jetour",
            "Changan",
            "Dongfeng",
            "Skywell",
            "Voyah",
            "Lada",
            "BAIC",
            "GAC",
        ):
            self.assertTrue(brand_uses_olx_text_search(brand), brand)

    def test_path_brands_stay_on_taxonomy(self):
        for brand in ("Toyota", "BMW", "BYD", "Geely", "JAC", "Chery", "Tesla", "MG"):
            self.assertFalse(brand_uses_olx_text_search(brand), brand)

    def test_text_search_uses_brand_only_url(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Zeekr", model="001", currency="USD")
        )
        self.assertEqual(params.text_query, "Zeekr")
        self.assertEqual(params.model_label, "001")
        self.assertIn("/q-zeekr/", build_search_url(params))
        self.assertNotIn("001", build_search_url(params))

    def test_haval_url(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Haval", model="Jolion", currency="USD")
        )
        self.assertEqual(params.text_query, "Haval")
        self.assertIn("/q-haval/", build_search_url(params))

    def test_post_filter_keeps_model(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Zeekr", model="001", currency="USD")
        )
        keep = OlxListing(title="Zeekr 001 WE 2025", price="20500", currency="USD")
        drop = OlxListing(title="Zeekr 7x повний привід", price="45900", currency="USD")
        junk = OlxListing(title="Коврики EVA універсальні", price="500", currency="UAH")
        self.assertTrue(passes_olx_filters(keep, params))
        self.assertFalse(passes_olx_filters(drop, params))
        self.assertFalse(passes_olx_filters(junk, params))

    def test_jaecoo_j7_matches_jaecoo_7(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Jaecoo", model="J7", currency="USD")
        )
        keep = OlxListing(title="Jaecoo 7 Urban, 2025", price="25000", currency="USD")
        drop = OlxListing(title="Jaecoo 5 Premium", price="22000", currency="USD")
        self.assertTrue(passes_olx_filters(keep, params))
        self.assertFalse(passes_olx_filters(drop, params))

    def test_rejects_parts_and_scooters(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Haval", model="Jolion", currency="USD")
        )
        headlight = OlxListing(
            title="Фара для Haval Jolion",
            price="200",
            currency="USD",
            specs={"Тип запчастини": "Фара"},
        )
        self.assertFalse(passes_olx_filters(headlight, params))

        nio = filters_to_olx_params(SearchFilters(brand="NIO", currency="USD"))
        scooter = OlxListing(
            title="Електроскутер Fada Nio 2000W",
            price="500",
            currency="USD",
            raw_params={"category": {"id": 1941}},
        )
        self.assertFalse(passes_olx_filters(scooter, nio))

    def test_rejects_genesis_apartments(self):
        params = filters_to_olx_params(SearchFilters(brand="Genesis", currency="USD"))
        apt = OlxListing(
            title="Продам 1к квартиру ЖК GENESIS Шулявка",
            price="80000",
            currency="USD",
        )
        car = OlxListing(
            title="Genesis G70 Elite 3.3T AWD 2018",
            price="22000",
            currency="USD",
        )
        self.assertFalse(passes_olx_filters(apt, params))
        self.assertTrue(passes_olx_filters(car, params))


if __name__ == "__main__":
    unittest.main()
