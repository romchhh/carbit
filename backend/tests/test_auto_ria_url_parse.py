from __future__ import annotations

import unittest

from app.services.auto_ria.url_parse import listing_id_from_external_url, omni_id_from_search_filters, parse_auto_ria_url


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

    def test_parse_new_listing_url(self):
        url = "https://auto.ria.com/uk/newauto/auto-12345.html"
        self.assertEqual(parse_auto_ria_url(url), ("12345", "new"))
        self.assertEqual(listing_id_from_external_url(url), "new_auto_ria_12345")

    def test_omni_id_from_numeric_brand(self):
        from app.schemas.schemas import SearchFilters

        self.assertEqual(
            omni_id_from_search_filters(SearchFilters(brand="40351832")),
            "40351832",
        )

    def test_model_001_is_not_omni_id(self):
        from app.schemas.schemas import SearchFilters

        self.assertIsNone(
            omni_id_from_search_filters(SearchFilters(brand="Zeekr", model="001")),
        )

    def test_omni_id_from_url_in_model(self):
        from app.schemas.schemas import SearchFilters

        url = "https://auto.ria.com/uk/auto_zeekr_001_40349889.html"
        self.assertEqual(
            omni_id_from_search_filters(SearchFilters(brand="Zeekr", model=url)),
            "40349889",
        )

    def test_short_numeric_brand_not_omni_id(self):
        from app.schemas.schemas import SearchFilters

        self.assertIsNone(omni_id_from_search_filters(SearchFilters(brand="911")))


if __name__ == "__main__":
    unittest.main()
