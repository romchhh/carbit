"""Тести keyword/alias для OLX і Telegram."""

from __future__ import annotations

import unittest

from app.schemas.schemas import SearchFilters
from app.services.search.brand_model_keywords import (
    build_search_keyword_queries,
    build_telegram_keyword_queries,
    collect_brand_keyword_variants,
    collect_model_keyword_variants,
    decode_telegram_scan_job,
    encode_telegram_scan_job,
    message_matches_search_filters,
    text_matches_brand_filter,
    text_matches_model_filter,
)
from app.services.telegram_channels.keyword_refresh import build_telegram_keyword_query
from app.services.telegram_channels.mapper import listing_out_matches_filters


class BrandModelKeywordTests(unittest.TestCase):
    def test_mercedes_brand_variants_include_ru(self):
        variants = collect_brand_keyword_variants("Mercedes-Benz")
        joined = " ".join(variants).lower()
        self.assertIn("mersedes", joined)
        self.assertIn("мерседес", joined)
        self.assertIn("mercedes", joined)

    def test_tesla_model_s_variants(self):
        variants = collect_model_keyword_variants("Tesla", "Model S")
        joined = " ".join(variants).lower()
        self.assertIn("model s", joined)
        self.assertTrue(any("модел" in v or "модель" in v for v in variants))

    def test_bmw_series_ru_variants(self):
        variants = collect_model_keyword_variants("BMW", "3 Series")
        joined = " ".join(variants).lower()
        self.assertIn("3 серии", joined)

    def test_search_queries_mix_latin_and_cyrillic(self):
        queries = build_search_keyword_queries("Toyota", "Camry", max_queries=10)
        self.assertGreaterEqual(len(queries), 3)
        joined = " | ".join(queries).lower()
        self.assertIn("toyota", joined)
        self.assertTrue("тойота" in joined or "камри" in joined or "camry" in joined)

    def test_telegram_scan_job_roundtrip(self):
        job = encode_telegram_scan_job("Tesla", "Model S")
        payload = decode_telegram_scan_job(job)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["brand"], "Tesla")
        self.assertEqual(payload["model"], "Model S")
        queries = build_telegram_keyword_queries(
            SearchFilters(brand="Tesla", model="Model S", currency="UAH")
        )
        self.assertEqual(len(queries), 1)
        self.assertEqual(decode_telegram_scan_job(queries[0]), payload)
        self.assertEqual(
            build_telegram_keyword_query(
                SearchFilters(brand="Tesla", model="Model S", currency="UAH")
            ),
            job,
        )

    def test_message_matches_all_variants(self):
        self.assertTrue(
            message_matches_search_filters("Продам Тесла модел S 100D", "Tesla", "Model S")
        )
        self.assertFalse(
            message_matches_search_filters("Продам Тесла модел 3", "Tesla", "Model S")
        )

    def test_cyrillic_brand_matches_filter(self):
        self.assertTrue(text_matches_brand_filter("Продам мерседес GLA 2020", "Mercedes-Benz"))
        self.assertTrue(text_matches_brand_filter("БМВ X5 2019", "BMW"))
        self.assertTrue(text_matches_brand_filter("тойота камри hybrid", "Toyota"))

    def test_cyrillic_model_matches_filter(self):
        self.assertTrue(
            text_matches_model_filter("продаю камри 2.5", "Camry", brand="Toyota")
        )
        self.assertTrue(
            text_matches_model_filter("мерседес e класс 220", "E-Class", brand="Mercedes-Benz")
        )
        self.assertTrue(
            text_matches_model_filter("Tesla model S plaid", "Model S", brand="Tesla")
        )

    def test_telegram_listing_matches_cyrillic_title(self):
        item = type("Item", (), {
            "brand": "",
            "model": "",
            "title": "Продам",
            "year": 2020,
            "price": 800_000,
            "currency": "UAH",
            "mileage": 50_000,
            "region": "Україна",
            "source": "telegram",
            "fuel": "",
            "transmission": "",
            "description": "Продам тойота камрі 2020, повний, без ДТП",
        })()
        filters = SearchFilters.model_validate({
            "brand": "Toyota",
            "model": "Camry",
            "sources": ["telegram"],
        })
        self.assertTrue(listing_out_matches_filters(item, filters))

    def test_sql_tokens_skip_single_letter_noise(self):
        from app.services.search.brand_model_keywords import filter_sql_search_tokens

        variants = ("Model S", "model-s", "s", "models", "модел s", "model s plaid")
        safe = filter_sql_search_tokens(variants)
        self.assertIn("Model S", safe)
        self.assertFalse(any(v.lower() == "s" for v in safe))
        self.assertFalse(any(v.lower() == "models" for v in safe))

    def test_telegram_rejects_wrong_model(self):
        item = type("Item", (), {
            "brand": "Tesla",
            "model": "",
            "title": "Tesla Model 3",
            "year": 2022,
            "price": 600_000,
            "currency": "UAH",
            "mileage": 30_000,
            "region": "Україна",
            "source": "telegram",
            "fuel": "Електро",
            "transmission": "",
            "description": "",
        })()
        filters = SearchFilters.model_validate({
            "brand": "Tesla",
            "model": "Model S",
            "sources": ["telegram"],
        })
        self.assertFalse(listing_out_matches_filters(item, filters))

    def test_tesla_model3_colloquial_titles(self):
        from app.schemas.schemas import SearchFilters
        from app.services.olx.mapper import filters_to_olx_params
        from app.services.olx.parser import OlxListing, passes_olx_filters

        params = filters_to_olx_params(
            SearchFilters(brand="Tesla", model="Model 3", currency="UAH")
        )
        titles = (
            "Продаж model 3 long range dual motor",
            "Тесла 3 2018 Перформанс Tesla 3 82kwt Performance 2018",
            "Tesla Model 3 Performance 2022",
        )
        for title in titles:
            listing = OlxListing(title=title, price="18000", currency="USD")
            self.assertTrue(passes_olx_filters(listing, params), title)
            self.assertTrue(
                message_matches_search_filters(title, "Tesla", "Model 3"), title
            )

    def test_tesla_model_y_colloquial(self):
        from app.schemas.schemas import SearchFilters
        from app.services.olx.mapper import filters_to_olx_params
        from app.services.olx.parser import OlxListing, passes_olx_filters

        params = filters_to_olx_params(
            SearchFilters(brand="Tesla", model="Model Y", currency="UAH")
        )
        title = "Продам Tesla Y 2021"
        listing = OlxListing(title=title, price="25000", currency="USD")
        self.assertTrue(passes_olx_filters(listing, params))
        self.assertTrue(message_matches_search_filters(title, "Tesla", "Model Y"))

    def test_bmw_shorthand_variants(self):
        variants = collect_model_keyword_variants("BMW", "X5")
        joined = " ".join(variants).lower()
        self.assertIn("bmw x5", joined)
        self.assertTrue(
            text_matches_model_filter("Продам БМВ X5 2019 xDrive", "X5", brand="BMW")
        )
        self.assertTrue(
            text_matches_model_filter("продаю bmw x5 30d", "X5", brand="BMW")
        )

    def test_bmw_3_series_shorthand(self):
        self.assertTrue(
            message_matches_search_filters("БМВ 3 2018 320i", "BMW", "3 Series")
        )
        self.assertTrue(
            text_matches_model_filter("bmw 3 series 320", "3 Series", brand="BMW")
        )

    def test_hyundai_tucson_shorthand(self):
        self.assertTrue(
            message_matches_search_filters("Продам хендай тucson 2020", "Hyundai", "Tucson")
        )
        self.assertTrue(
            text_matches_model_filter("hyundai tucson 1.6", "Tucson", brand="Hyundai")
        )

    def test_toyota_prado_shorthand(self):
        self.assertTrue(
            message_matches_search_filters("Toyota prado 150 2019", "Toyota", "Land Cruiser Prado")
        )
        self.assertTrue(
            message_matches_search_filters("продаю прадо 2018", "Toyota", "Land Cruiser Prado")
        )

    def test_vw_golf_brand_shorthand(self):
        self.assertTrue(
            message_matches_search_filters("VW Golf 7 GTI", "Volkswagen", "Golf")
        )
        self.assertTrue(
            text_matches_model_filter("фольксваген гольф 6", "Golf", brand="Volkswagen")
        )

    def test_audi_a4_shorthand(self):
        self.assertTrue(
            message_matches_search_filters("Audi A4 2.0 TDI", "Audi", "A4")
        )
        self.assertTrue(
            text_matches_model_filter("ауди а4 b8", "A4", brand="Audi")
        )

    def test_nissan_qashqai_cyrillic(self):
        self.assertTrue(
            message_matches_search_filters("Нissan кашкай 2017", "Nissan", "Qashqai")
        )

    def test_unique_model_without_brand_in_title(self):
        self.assertTrue(
            message_matches_search_filters("Продаж camry hybrid 2020", "Toyota", "Camry")
        )

    def test_zeekr_001_all_variants(self):
        from app.schemas.schemas import SearchFilters
        from app.services.olx.mapper import filters_to_olx_params
        from app.services.olx.parser import OlxListing, passes_olx_filters

        params = filters_to_olx_params(
            SearchFilters(brand="Zeekr", model="001", currency="UAH")
        )
        titles_ok = (
            "Zeekr 001 You 2024",
            "Зікр 001 You 2024",
            "001 You 2024",
            "продаю 001 you",
            "ZEEKR001 2023",
            "продаю зикр 001",
            "001 Zeekr",
        )
        for title in titles_ok:
            listing = OlxListing(title=title, price="34000", currency="USD")
            self.assertTrue(message_matches_search_filters(title, "Zeekr", "001"), title)
            self.assertTrue(passes_olx_filters(listing, params), title)

        self.assertFalse(
            message_matches_search_filters("Zeekr 7x повний привід", "Zeekr", "001")
        )

    def test_zeekr_cyrillic_brand_filter(self):
        self.assertTrue(
            message_matches_search_filters("Зікр 001 You 2024", "Зікр", "001")
        )

    def test_zeekr_007_009_x(self):
        cases = (
            ("Zeekr 007", "007"),
            ("зикр007", "007"),
            ("009 зікр", "009"),
            ("Zeekr X 2024", "X"),
            ("Зикр X Long Range", "X"),
        )
        for title, model in cases:
            self.assertTrue(
                message_matches_search_filters(title, "Zeekr", model), f"{title}/{model}"
            )


if __name__ == "__main__":
    unittest.main()
