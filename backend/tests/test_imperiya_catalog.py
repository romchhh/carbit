from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.services.imperiya.catalog import (
    _imperiya_model_key,
    resolve_make_id,
    resolve_model_id,
)
from app.services.search.subbrand_split import split_huawei_subbrand


class SubbrandSplitTests(unittest.TestCase):
    def test_huawei_aito_m5(self):
        self.assertEqual(split_huawei_subbrand("Huawei", "Aito M5"), ("Aito", "M5"))

    def test_huawei_luxeed_r7(self):
        self.assertEqual(split_huawei_subbrand("Huawei", "Luxeed R7"), ("Luxeed", "R7"))

    def test_huawei_seres_sf5(self):
        self.assertEqual(split_huawei_subbrand("Huawei", "Seres SF5"), ("Seres", "SF5"))

    def test_other_brand_unchanged(self):
        self.assertEqual(split_huawei_subbrand("BMW", "X5"), ("BMW", "X5"))


class ImperiyaCatalogTests(unittest.TestCase):
    def test_imperiya_model_key_class_series(self):
        self.assertEqual(_imperiya_model_key("S-Класс"), "s-class")
        self.assertEqual(_imperiya_model_key("S-Class"), "s-class")
        self.assertEqual(_imperiya_model_key("3 серії"), "3 series")

    def test_resolve_model_id_mercedes_s_class(self):
        async def run() -> int | None:
            client = AsyncMock()
            with patch(
                "app.services.imperiya.catalog._load_models",
                new=AsyncMock(
                    return_value=[
                        {"id": 2412, "name": "S-Класс", "slug": "mercedes-benz-s-klass"},
                        {"id": 2413, "name": "S-Класс AMG", "slug": "mercedes-benz-s-klass-amg"},
                        {"id": 2356, "name": "Citan", "slug": "mercedes-benz-citan"},
                    ]
                ),
            ):
                return await resolve_model_id(
                    client, 207, "S-Class", brand="Mercedes-Benz"
                )

        self.assertEqual(asyncio.run(run()), 2412)

    def test_resolve_model_id_bmw_3_series(self):
        async def run() -> int | None:
            client = AsyncMock()
            with patch(
                "app.services.imperiya.catalog._load_models",
                new=AsyncMock(
                    return_value=[
                        {"id": 256, "name": "3 серії", "slug": "bmw-3-seriyi"},
                        {"id": 257, "name": "3/15", "slug": "bmw-3-15"},
                    ]
                ),
            ):
                return await resolve_model_id(client, 41, "3 Series", brand="BMW")

        self.assertEqual(asyncio.run(run()), 256)

    def test_resolve_model_id_zeekr_001(self):
        async def run() -> int | None:
            client = AsyncMock()
            with patch(
                "app.services.imperiya.catalog._load_models",
                new=AsyncMock(
                    return_value=[
                        {"id": 3891, "name": "001", "slug": "zeekr-001"},
                        {"id": 3892, "name": "007", "slug": "zeekr-007"},
                    ]
                ),
            ):
                return await resolve_model_id(client, 351, "001", brand="Zeekr")

        self.assertEqual(asyncio.run(run()), 3891)

    def test_resolve_make_id_mercedes_aliases(self):
        async def run() -> int | None:
            client = AsyncMock()
            with patch(
                "app.services.imperiya.catalog._load_makes",
                new=AsyncMock(
                    return_value=[
                        {"id": 207, "name": "Mercedes-Benz", "slug": "mercedes-benz"},
                        {"id": 41, "name": "BMW", "slug": "bmw"},
                    ]
                ),
            ):
                return await resolve_make_id(client, "Mercedes-Benz")

        self.assertEqual(asyncio.run(run()), 207)


if __name__ == "__main__":
    unittest.main()
