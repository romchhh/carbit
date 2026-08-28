"""Latin + кирилиця в пошуку марок/моделей."""

from __future__ import annotations

import unittest

from app.core.text import (
    letter_class_canonical,
    letter_class_display,
    letter_class_search_tokens,
    unify_class_spelling,
)
from app.services.search.brand_model_keywords import (
    canonical_search_model,
    collect_model_keyword_variants,
    filter_sql_search_tokens,
    message_matches_search_filters,
)


class ScriptNormalizationTests(unittest.TestCase):
    def test_unify_class_spelling_latin_and_cyrillic(self):
        self.assertEqual(unify_class_spelling("G-Class"), "g class")
        self.assertEqual(unify_class_spelling("G-Класс AMG"), "g class amg")
        self.assertEqual(unify_class_spelling("C клас"), "c class")
        self.assertEqual(unify_class_spelling("с клас"), "c class")
        self.assertEqual(unify_class_spelling("С-клас"), "c class")

    def test_letter_class_canonical_from_cyrillic_filter(self):
        self.assertEqual(letter_class_canonical("G-Класс"), "g-class")
        self.assertEqual(letter_class_canonical("G-Класс AMG"), "g-class")
        self.assertEqual(letter_class_canonical("G Class"), "g-class")
        self.assertEqual(letter_class_display("G-Класс AMG"), "G-Class")
        self.assertEqual(canonical_search_model("G-Класс AMG"), "G-Class")
        self.assertEqual(letter_class_canonical("с клас"), "c-class")
        self.assertEqual(letter_class_canonical("С-клас"), "c-class")
        self.assertEqual(canonical_search_model("С клас"), "C-Class")

    def test_g_class_sql_has_both_scripts(self):
        tokens = filter_sql_search_tokens(
            collect_model_keyword_variants("Mercedes-Benz", "G-Class"),
            limit=8,
        )
        joined = " | ".join(t.lower() for t in tokens)
        self.assertIn("g-class", joined)
        self.assertIn("g-класс", joined)

    def test_g_class_matches_cyrillic_and_latin_posts(self):
        brand = "Mercedes-Benz"
        model = "G-Class"
        cyr = "🔴 Марка: Mercedes-Benz | Модель: G-Класс AMG | Рік: 2022"
        lat = "Mercedes-Benz G-Class G63 2022"
        self.assertTrue(message_matches_search_filters(cyr, brand, model))
        self.assertTrue(message_matches_search_filters(lat, brand, model))

    def test_g_class_filter_works_with_cyrillic_model_input(self):
        brand = "Mercedes-Benz"
        text = "Mercedes-Benz G-Class G63"
        self.assertTrue(message_matches_search_filters(text, brand, "G-Класс"))
        self.assertTrue(message_matches_search_filters(text, brand, "G Класс"))

    def test_letter_class_search_tokens_mixed_scripts(self):
        tokens = letter_class_search_tokens("g")
        self.assertIn("g-класс", [t.lower() for t in tokens])
        self.assertIn("g-class", [t.lower() for t in tokens])
        self.assertIn("G-Class", tokens)

    def test_audi_e_tron_canonical(self):
        self.assertEqual(canonical_search_model("e tron"), "E-tron")
        self.assertEqual(canonical_search_model("E-Tron"), "E-tron")
        self.assertEqual(canonical_search_model("e-tron gt"), "E-tron GT")


if __name__ == "__main__":
    unittest.main()
