"""Тести квоти VIN-перевірок."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.models.models import PlanTier


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = value


class VinQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_free_allows_three_unique_vins(self) -> None:
        from app.services.vin_quota import enforce_vin_check_quota

        redis = FakeRedis()
        user = SimpleNamespace(id="u1", plan=PlanTier.free, plan_expires_at=None)

        with patch("app.services.vin_quota.get_redis", AsyncMock(return_value=redis)):
            self.assertEqual(await enforce_vin_check_quota(user, "WAUZZZ1"), 2)
            self.assertEqual(await enforce_vin_check_quota(user, "WAUZZZ2"), 1)
            self.assertEqual(await enforce_vin_check_quota(user, "WAUZZZ3"), 0)
            self.assertEqual(await enforce_vin_check_quota(user, "WAUZZZ1"), 0)
            with self.assertRaises(HTTPException) as ctx:
                await enforce_vin_check_quota(user, "WAUZZZ4")
            self.assertEqual(ctx.exception.status_code, 402)
            self.assertEqual(ctx.exception.detail["code"], "vin_check_limit")
            self.assertEqual(ctx.exception.detail["upgrade_plan"], "lite")

    async def test_paid_unlimited(self) -> None:
        from app.services.vin_quota import enforce_vin_check_quota

        redis = FakeRedis()
        user = SimpleNamespace(id="u2", plan=PlanTier.lite, plan_expires_at=None)

        with patch("app.services.vin_quota.get_redis", AsyncMock(return_value=redis)):
            for i in range(10):
                remaining = await enforce_vin_check_quota(user, f"VIN{i:014d}X")
                self.assertIsNone(remaining)


if __name__ == "__main__":
    unittest.main()
