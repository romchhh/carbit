from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.admin.geo_ip import (
    country_from_maxmind,
    is_private_ip,
    resolve_country_code,
    resolve_visit_country,
)


class GeoIpHelpersTests(unittest.TestCase):
    def test_private_ip(self):
        self.assertTrue(is_private_ip("127.0.0.1"))
        self.assertTrue(is_private_ip("10.0.0.5"))
        self.assertFalse(is_private_ip("8.8.8.8"))

    def test_country_from_maxmind_without_db(self):
        self.assertIsNone(country_from_maxmind("8.8.8.8"))


class GeoIpResolveTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_country_code_uses_cache(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="PL")

        with patch("app.services.admin.geo_ip.get_redis", AsyncMock(return_value=redis)):
            code = await resolve_country_code("91.123.45.67")

        self.assertEqual(code, "PL")
        redis.setex.assert_not_called()

    async def test_resolve_country_code_private_ip(self):
        code = await resolve_country_code("127.0.0.1")
        self.assertEqual(code, "XX")

    async def test_resolve_country_code_http_lookup(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"status": "success", "countryCode": "UA"}

        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.admin.geo_ip.get_redis", AsyncMock(return_value=redis)):
            with patch("app.services.admin.geo_ip.country_from_maxmind", return_value=None):
                with patch("app.services.admin.geo_ip.httpx.AsyncClient", return_value=client):
                    code = await resolve_country_code("91.123.45.67")

        self.assertEqual(code, "UA")
        redis.setex.assert_awaited_once()

    async def test_resolve_visit_country_from_ip(self):
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="91.123.45.67")

        with patch(
            "app.services.admin.geo_ip.resolve_country_code",
            AsyncMock(return_value="UA"),
        ):
            code = await resolve_visit_country(request)

        self.assertEqual(code, "UA")


if __name__ == "__main__":
    unittest.main()
