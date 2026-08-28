"""Пробний «Старт» 7 днів після реєстрації → Free."""

from __future__ import annotations

import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.timezone import now_kyiv
from app.models.models import PlanTier
from app.services.billing.plans import (
    SIGNUP_TRIAL_DAYS,
    SIGNUP_TRIAL_PLAN_ID,
    effective_searches_limit,
    enforce_plan_expiry,
    grant_signup_trial,
)


class GrantSignupTrialTests(unittest.TestCase):
    def test_grants_lite_for_seven_days(self):
        user = SimpleNamespace(
            plan=PlanTier.free,
            plan_expires_at=None,
            trial_ends_at=None,
        )
        before = now_kyiv()
        grant_signup_trial(user)

        self.assertEqual(user.plan, PlanTier.lite)
        self.assertEqual(user.plan.value, SIGNUP_TRIAL_PLAN_ID)
        self.assertIsNotNone(user.plan_expires_at)
        self.assertIsNotNone(user.trial_ends_at)
        delta = user.plan_expires_at - before
        self.assertGreaterEqual(delta, timedelta(days=SIGNUP_TRIAL_DAYS - 1))
        self.assertEqual(effective_searches_limit(user), 10)

    def test_expired_signup_trial_downgrades_to_free(self):
        user = SimpleNamespace(
            plan=PlanTier.lite,
            plan_expires_at=now_kyiv() - timedelta(hours=1),
            trial_ends_at=now_kyiv() - timedelta(hours=1),
        )
        changed = enforce_plan_expiry(user)
        self.assertTrue(changed)
        self.assertEqual(user.plan, PlanTier.free)
        self.assertIsNone(user.plan_expires_at)
        self.assertIsNone(user.trial_ends_at)
        self.assertEqual(effective_searches_limit(user), 1)


class ExpirePaidPlansTests(unittest.IsolatedAsyncioTestCase):
    async def test_skips_users_with_active_subscription(self):
        from app.services.billing.maintenance import expire_paid_plans

        user = SimpleNamespace(
            id="u1",
            plan=PlanTier.lite,
            plan_expires_at=now_kyiv() - timedelta(hours=1),
            trial_ends_at=now_kyiv() - timedelta(hours=1),
        )

        db = AsyncMock()
        db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[user])))
        db.scalar = AsyncMock(return_value="sub_active")
        db.flush = AsyncMock()

        with patch(
            "app.services.billing.maintenance.enforce_active_searches_quota",
            AsyncMock(),
        ):
            changed = await expire_paid_plans(db)

        self.assertEqual(changed, 0)
        self.assertEqual(user.plan, PlanTier.lite)


if __name__ == "__main__":
    unittest.main()
