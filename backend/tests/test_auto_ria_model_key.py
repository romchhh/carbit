from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.services.auto_ria.catalog import _model_catalog_match, _normalize_model_key, resolve_model_id


class AutoRiaModelKeyTests(unittest.TestCase):
    def test_coupe_aliases(self):
        self.assertEqual(_normalize_model_key("GLE Coupe"), "gle coupe")
        self.assertEqual(_normalize_model_key("GLE-Class Coupe"), "gle coupe")
        self.assertEqual(_normalize_model_key("GLE (купе)"), "gle coupe")
        self.assertEqual(_normalize_model_key("GLC-Class Coupe"), "glc coupe")
        self.assertEqual(_normalize_model_key("CLE-Class"), "cle")
        self.assertEqual(_normalize_model_key("C-Класс Купе"), "c coupe")
        self.assertEqual(_normalize_model_key("C-клас Купе"), "c coupe")
        self.assertEqual(_normalize_model_key("GLC-Класс Купе"), "glc coupe")

    def test_c_class_coupe_not_glc_partial(self):
        target = "C-Class Coupe"
        target_key = _normalize_model_key(target)
        self.assertFalse(
            _model_catalog_match(
                target,
                target_key,
                "GLC-Class Coupe",
                "glc-class coupe",
                _normalize_model_key("GLC-Class Coupe"),
            )
        )
        self.assertTrue(
            _model_catalog_match(
                target,
                target_key,
                "C-Class Coupe",
                "c-class coupe",
                _normalize_model_key("C-Class Coupe"),
            )
        )


class AutoRiaModelResolveTests(unittest.IsolatedAsyncioTestCase):
    async def test_c_class_coupe_resolves_cyrillic_catalog_name(self):
        models = [
            {"name": "C-Class", "value": 1},
            {"name": "C-Класс Купе", "value": 3},
            {"name": "GLC-Class Coupe", "value": 4},
        ]
        client = AsyncMock()
        with patch("app.services.auto_ria.catalog._load_models", return_value=models):
            model_id = await resolve_model_id(client, 47, "C-Class Coupe")
        self.assertEqual(model_id, 3)


if __name__ == "__main__":
    unittest.main()
