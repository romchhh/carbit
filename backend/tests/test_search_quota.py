"""Квота активних моніторингів після кінця trial / downgrade."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


class EnforceActiveSearchesQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_pauses_excess_after_trial_limit_drops(self):
        from app.services.billing.plans import enforce_active_searches_quota

        now = datetime.now(timezone.utc)
        kept = SimpleNamespace(id="keep", is_active=True, created_at=now - timedelta(days=3))
        excess_a = SimpleNamespace(id="a", is_active=True, created_at=now - timedelta(days=2))
        excess_b = SimpleNamespace(id="b", is_active=True, created_at=now - timedelta(days=1))

        result = MagicMock()
        result.all.return_value = [kept, excess_a, excess_b]

        db = AsyncMock()
        db.scalars = AsyncMock(return_value=result)
        db.flush = AsyncMock()

        user = SimpleNamespace(
            id="u1",
            plan=SimpleNamespace(value="free"),
            is_trial_active=False,
            plan_expires_at=None,
        )

        paused = await enforce_active_searches_quota(db, user)

        self.assertEqual(paused, 2)
        self.assertTrue(kept.is_active)
        self.assertFalse(excess_a.is_active)
        self.assertFalse(excess_b.is_active)
        db.flush.assert_awaited_once()

    async def test_noop_when_within_limit(self):
        from app.services.billing.plans import enforce_active_searches_quota

        only = SimpleNamespace(id="keep", is_active=True, created_at=datetime.now(timezone.utc))
        result = MagicMock()
        result.all.return_value = [only]
        db = AsyncMock()
        db.scalars = AsyncMock(return_value=result)
        db.flush = AsyncMock()

        user = SimpleNamespace(
            id="u1",
            plan=SimpleNamespace(value="free"),
            is_trial_active=False,
            plan_expires_at=None,
        )

        paused = await enforce_active_searches_quota(db, user)
        self.assertEqual(paused, 0)
        self.assertTrue(only.is_active)
        db.flush.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
