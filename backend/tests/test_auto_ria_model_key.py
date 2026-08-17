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

    async def test_s_class_not_sprinter(self):
        models = [
            {"name": "Sprinter", "value": 100},
            {"name": "SL", "value": 101},
            {"name": "S-Класс", "value": 102},
            {"name": "S-Класс AMG", "value": 103},
        ]
        client = AsyncMock()
        with patch("app.services.auto_ria.catalog._load_models", return_value=models):
            model_id = await resolve_model_id(client, 47, "S-Class")
        self.assertEqual(model_id, 102)

    async def test_s_class_coupe_prefers_coupe_variant(self):
        models = [
            {"name": "S-Класс", "value": 102},
            {"name": "S-Класс Купе", "value": 104},
        ]
        client = AsyncMock()
        with patch("app.services.auto_ria.catalog._load_models", return_value=models):
            model_id = await resolve_model_id(client, 47, "S-Class Coupe")
        self.assertEqual(model_id, 104)


class NewAutoPhotoUrlTests(unittest.TestCase):
    def test_appends_newauto_cdn_suffix(self):
        from app.services.auto_ria.mapper import _new_auto_photo_urls

        base = "https://cdn.riastatic.com/photosnewr/auto/new_auto_storage/bmw-5-series__3848966"
        urls = _new_auto_photo_urls([base, f"{base}.jpg", ""])
        self.assertEqual(
            urls[0],
            f"{base}-620x465x90.jpg",
        )
        self.assertEqual(urls[1], f"{base}.jpg")
        self.assertEqual(len(urls), 2)


if __name__ == "__main__":
    unittest.main()
