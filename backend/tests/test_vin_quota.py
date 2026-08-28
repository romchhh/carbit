"""Тести квоти VIN-перевірок."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.models import PlanTier


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = value


class VinQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_free_unlimited(self) -> None:
        from app.services.vin_quota import enforce_vin_check_quota

        redis = FakeRedis()
        user = SimpleNamespace(id="u1", plan=PlanTier.free, plan_expires_at=None)

        with patch("app.services.vin_quota.get_redis", AsyncMock(return_value=redis)):
            for i in range(5):
                remaining = await enforce_vin_check_quota(user, f"VIN{i:014d}X")
                self.assertIsNone(remaining)

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
