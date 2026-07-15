from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services.baza_gai.client import BazaGaiClient
from app.services.baza_gai.errors import BazaGaiNotFound, BazaGaiRateLimited
from app.services.baza_gai.service import map_baza_gai_vin_payload, normalize_vin

SAMPLE_VIN_PAYLOAD = {
    "digits": "KA0007XB",
    "vin": "WBA7B41080G157838",
    "region": {
        "name": "г. Киев",
        "name_ua": "м. Київ",
        "slug": "kyiv",
        "old_code": "AA",
        "new_code": "KA",
    },
    "vendor": "BMW",
    "model": "M760LI",
    "model_year": 2021,
    "photo_url": "https://baza-gai.com.ua/catalog-images/bmw.jpg",
    "is_stolen": False,
    "stolen_details": None,
    "operations": [
        {
            "digits": "KA0007XB",
            "is_last": True,
            "registered_at": "03.04.2021",
            "model_year": 2021,
            "vendor": "BMW",
            "model": "M760LI",
            "operation": {
                "ru": "Первичная регистрация",
                "ua": "Первинна реєстрація",
            },
            "department": "ТСЦ 8047",
            "color": {"slug": "gray", "ru": "Серый", "ua": "Сірий"},
            "address": "м.Київ, Деснянський",
            "displacement": 6592,
        }
    ],
}


class NormalizeVinTests(unittest.TestCase):
    def test_normalizes_and_validates(self):
        self.assertEqual(normalize_vin(" wba7b41080g157838 "), "WBA7B41080G157838")
        self.assertIsNone(normalize_vin("short"))
        self.assertIsNone(normalize_vin("WBA7B41080G15783I"))  # I недопустима
        self.assertIsNone(normalize_vin(None))


class MapPayloadTests(unittest.TestCase):
    def test_maps_docs_sample(self):
        out = map_baza_gai_vin_payload(SAMPLE_VIN_PAYLOAD, vin="WBA7B41080G157838")
        self.assertEqual(out.vin, "WBA7B41080G157838")
        self.assertEqual(out.plate, "KA0007XB")
        self.assertEqual(out.vendor, "BMW")
        self.assertEqual(out.model, "M760LI")
        self.assertEqual(out.model_year, 2021)
        self.assertFalse(out.is_stolen)
        self.assertEqual(out.region.name_ua, "м. Київ")
        self.assertEqual(out.region.codes, ["AA", "KA"])
        self.assertEqual(len(out.operations), 1)
        op = out.operations[0]
        self.assertEqual(op.operation_ua, "Первинна реєстрація")
        self.assertEqual(op.color, "Сірий")
        self.assertEqual(op.displacement, 6592)
        self.assertEqual(op.department, "ТСЦ 8047")
        self.assertEqual(out.registrations_count, 1)
        self.assertEqual(out.color, "Сірий")
        self.assertEqual(out.displacement, 6592)
        self.assertFalse(out.is_stolen)
        self.assertTrue(out.source_url.endswith("/vin/WBA7B41080G157838"))


class ClientHttpTests(unittest.IsolatedAsyncioTestCase):
    async def _lookup_with_status(self, status: int):
        response = httpx.Response(
            status,
            request=httpx.Request("GET", "https://baza-gai.com.ua/vin/WBA7B41080G157838"),
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", return_value=mock_client):
            client = BazaGaiClient(api_key="test-key", base_url="https://baza-gai.com.ua")
            return await client.lookup_vin("WBA7B41080G157838")

    async def test_404_raises_not_found(self):
        with self.assertRaises(BazaGaiNotFound):
            await self._lookup_with_status(404)

    async def test_429_raises_rate_limited(self):
        with self.assertRaises(BazaGaiRateLimited):
            await self._lookup_with_status(429)


if __name__ == "__main__":
    unittest.main()
