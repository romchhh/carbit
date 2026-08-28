from __future__ import annotations

import unittest

from app.schemas.schemas import SearchFilters
from app.services.auto_ria.url_parse import (
    extract_numeric_listing_id,
    is_likely_numeric_model_code,
    listing_id_from_external_url,
    omni_id_from_search_filters,
    parse_auto_ria_url,
)

# (brand, model) — жодна комбінація не має давати omni_id
NUMERIC_MODEL_CASES = [
    ("Zeekr", "001"),
    ("Zeekr", "007"),
    ("Zeekr", "009"),
    ("Porsche", "911"),
    ("Porsche", "718"),
    ("Mazda", "3"),
    ("Mazda", "6"),
    ("Fiat", "500"),
    ("Peugeot", "208"),
    ("Peugeot", "3008"),
    ("BMW", "3 Series"),
    ("Avatr", "07"),
    ("Avatr", "11"),
    ("Lada", "2107"),
    ("McLaren", "720S"),
]


class AutoRiaUrlParseTests(unittest.TestCase):
    def test_parse_used_listing_url(self):
        url = "https://auto.ria.com/uk/auto_zeekr_001_40351832.html"
        self.assertEqual(parse_auto_ria_url(url), ("40351832", "used"))
        self.assertEqual(listing_id_from_external_url(url), "auto_ria_40351832")

    def test_parse_second_listing(self):
        url = "https://auto.ria.com/uk/auto_zeekr_001_40349889.html"
        self.assertEqual(listing_id_from_external_url(url), "auto_ria_40349889")

    def test_parse_internal_id(self):
        self.assertEqual(listing_id_from_external_url("auto_ria_40351832"), "auto_ria_40351832")

    def test_short_internal_id_rejected(self):
        self.assertIsNone(listing_id_from_external_url("auto_ria_001"))
        self.assertIsNone(listing_id_from_external_url("auto_ria_911"))
        self.assertIsNone(extract_numeric_listing_id("auto_ria_001"))

    def test_parse_new_listing_url(self):
        url = "https://auto.ria.com/uk/newauto/auto-12345.html"
        self.assertEqual(parse_auto_ria_url(url), ("12345", "new"))
        self.assertEqual(listing_id_from_external_url(url), "new_auto_ria_12345")

    def test_omni_id_from_numeric_brand(self):
        self.assertEqual(
            omni_id_from_search_filters(SearchFilters(brand="40351832")),
            "40351832",
        )

    def test_omni_id_from_numeric_brands_array(self):
        self.assertEqual(
            omni_id_from_search_filters(SearchFilters(brands=["40351832"])),
            "40351832",
        )

    def test_model_001_is_not_omni_id(self):
        self.assertIsNone(
            omni_id_from_search_filters(SearchFilters(brand="Zeekr", model="001")),
        )

    def test_models_array_numeric_not_omni_id(self):
        self.assertIsNone(
            omni_id_from_search_filters(SearchFilters(brands=["Zeekr"], models=["001"])),
        )

    def test_omni_id_from_url_in_model(self):
        url = "https://auto.ria.com/uk/auto_zeekr_001_40349889.html"
        self.assertEqual(
            omni_id_from_search_filters(SearchFilters(brand="Zeekr", model=url)),
            "40349889",
        )

    def test_omni_id_from_url_in_models_array(self):
        url = "https://auto.ria.com/uk/auto_porsche_911_40351832.html"
        self.assertEqual(
            omni_id_from_search_filters(SearchFilters(brands=["Porsche"], models=[url])),
            "40351832",
        )

    def test_omni_id_from_url_in_brand(self):
        url = "https://auto.ria.com/uk/auto_zeekr_001_40351832.html"
        self.assertEqual(
            omni_id_from_search_filters(SearchFilters(brand=url, model="001")),
            "40351832",
        )

    def test_short_numeric_brand_not_omni_id(self):
        self.assertIsNone(omni_id_from_search_filters(SearchFilters(brand="911")))

    def test_short_numeric_brands_array_not_omni_id(self):
        self.assertIsNone(omni_id_from_search_filters(SearchFilters(brands=["911"])))

    def test_is_likely_numeric_model_code(self):
        self.assertTrue(is_likely_numeric_model_code("001"))
        self.assertTrue(is_likely_numeric_model_code("911"))
        self.assertTrue(is_likely_numeric_model_code("3"))
        self.assertFalse(is_likely_numeric_model_code("40351832"))
        self.assertFalse(is_likely_numeric_model_code("Camry"))

    def test_numeric_models_never_become_omni_id(self):
        for brand, model in NUMERIC_MODEL_CASES:
            with self.subTest(brand=brand, model=model):
                self.assertIsNone(
                    omni_id_from_search_filters(SearchFilters(brand=brand, model=model)),
                    f"{brand} {model} must not set omni_id",
                )


if __name__ == "__main__":
    unittest.main()
