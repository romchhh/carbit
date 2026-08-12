"""Тести FE-каталогу для matching."""

from __future__ import annotations

import unittest

from app.services.search.fe_catalog import (
    load_fe_brand_models,
    unique_model_token_owner,
)


class FeCatalogTests(unittest.TestCase):
    def test_loads_full_catalog(self):
        fe = load_fe_brand_models()
        self.assertGreaterEqual(len(fe), 80)
        total = sum(len(v) for v in fe.values())
        self.assertGreaterEqual(total, 1400)

    def test_unique_camry_is_toyota(self):
        owners = unique_model_token_owner()
        self.assertEqual(owners.get("camry"), "toyota")

    def test_unique_zeekr_001_is_zeekr(self):
        owners = unique_model_token_owner()
        self.assertEqual(owners.get("001"), "zeekr")
        self.assertEqual(owners.get("009"), "zeekr")
        # «007» є і в Zeekr, і в Skywell — токен більше не однозначний.
        self.assertIsNone(owners.get("007"))

    def test_ambiguous_digit_not_unique(self):
        owners = unique_model_token_owner()
        self.assertNotIn("3", owners)


if __name__ == "__main__":
    unittest.main()
