"""Статичний AUTO.RIA каталог марок/моделей — без HTTP."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from app.services.auto_ria import catalog as ar_catalog
from app.services.auto_ria.catalog import resolve_mark_id, resolve_model_id


class AutoRiaStaticCatalogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        ar_catalog._marks_cache = None
        ar_catalog._models_cache.clear()

    async def test_resolves_zeekr_001_without_api(self):
        client = AsyncMock()
        mark_id = await resolve_mark_id(client, "Zeekr")
        model_id = await resolve_model_id(client, mark_id or 0, "001")
        client.get_marks.assert_not_called()
        client.get_models.assert_not_called()
        self.assertEqual(mark_id, 55280)
        self.assertEqual(model_id, 64237)

    async def test_resolves_bmw_without_api(self):
        client = AsyncMock()
        mark_id = await resolve_mark_id(client, "BMW")
        client.get_marks.assert_not_called()
        self.assertEqual(mark_id, 9)
        x5 = await resolve_model_id(client, 9, "X5")
        client.get_models.assert_not_called()
        self.assertIsInstance(x5, int)
        self.assertGreater(x5 or 0, 0)

    async def test_static_dump_covers_core_fe_brands(self):
        data = ar_catalog._static_catalog()
        marks = {str(item.get("name", "")).lower() for item in data.get("marks") or []}
        for name in ("bmw", "audi", "toyota", "zeekr", "mercedes-benz"):
            self.assertIn(name, marks)
        self.assertGreaterEqual(len(data.get("models") or {}), 90)
