"""Голосовий парсер: кожен запит повністю замінює набір фільтрів."""

from __future__ import annotations

import unittest

from app.services.ai.search_parser import _clean_filters, _enrich_filters_from_transcript


class VoiceFilterReplaceTests(unittest.TestCase):
    def test_new_query_does_not_keep_previous_brand_fields(self):
        query = "Toyota Camry 2019 дизель автомат у львівській області"
        raw_gpt = {
            "brand": "Toyota",
            "model": "Camry",
            "year_from": 2019,
            "fuels": ["Дизель"],
            "transmissions": ["Автомат"],
            "region": "Львівська область",
        }
        filters = _clean_filters(raw_gpt)
        filters = _enrich_filters_from_transcript(query, filters, raw_gpt)

        self.assertEqual(filters.get("brand"), "Toyota")
        self.assertEqual(filters.get("model"), "Camry")
        self.assertNotIn("price_to", filters)
        self.assertNotIn("Audi", str(filters))

    def test_budget_only_query_has_no_brand(self):
        query = "до 15000 доларів 2020-2022 у волинській області"
        raw_gpt = {
            "brand": None,
            "price_to": 15000,
            "currency": "USD",
            "year_from": 2020,
            "year_to": 2022,
            "region": "Волинська область",
        }
        filters = _clean_filters(raw_gpt)
        filters = _enrich_filters_from_transcript(query, filters, raw_gpt)

        self.assertNotIn("brand", filters)
        self.assertEqual(filters.get("price_to"), 15000)
        self.assertEqual(filters.get("region"), "Волинська область")

    def test_accepts_fuel_and_transmission_aliases(self):
        raw = {"fuels": ["Дизель"], "transmissions": ["Автомат"]}
        cleaned = _clean_filters(raw)
        self.assertEqual(cleaned.get("fuel"), ["Дизель"])
        self.assertEqual(cleaned.get("transmission"), ["Автомат"])

        raw_alt = {"fuel": ["Бензин"], "transmission": ["Механіка"]}
        cleaned_alt = _clean_filters(raw_alt)
        self.assertEqual(cleaned_alt.get("fuel"), ["Бензин"])
        self.assertEqual(cleaned_alt.get("transmission"), ["Механіка"])

    def test_omits_empty_array_filters(self):
        cleaned = _clean_filters({"brand": "BMW", "fuels": [], "sources": []})
        self.assertEqual(cleaned.get("brand"), "BMW")
        self.assertNotIn("fuel", cleaned)
        self.assertNotIn("sources", cleaned)


if __name__ == "__main__":
    unittest.main()
