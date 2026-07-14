"""Тести servicing підписок: failed charges + daily maintenance helpers."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.models import SubscriptionStatus
from app.services.billing.maintenance import MAX_FAILED_CHARGES


class FailedChargesTests(unittest.IsolatedAsyncioTestCase):
    async def test_second_failure_auto_cancels(self):
        from app.services.billing.subscriptions import handle_failed_recurring

        sub = SimpleNamespace(
            order_id="ord_1",
            user_id="u1",
            status=SubscriptionStatus.active,
            failed_charges=MAX_FAILED_CHARGES - 1,
            last_status=None,
            cancelled_at=None,
        )
        user = SimpleNamespace(id="u1", telegram_connected=False, telegram_id=None)
        db = AsyncMock()
        db.get = AsyncMock(return_value=user)
        db.flush = AsyncMock()

        with (
            patch(
                "app.services.billing.subscriptions.unsubscribe_order",
                AsyncMock(return_value={}),
            ) as unsub,
            patch(
                "app.services.billing.subscriptions.notify_payment_failed",
                AsyncMock(return_value=True),
            ) as notify,
        ):
            result = await handle_failed_recurring(db, sub=sub, status_raw="failure")

        self.assertTrue(result["cancelled"])
        self.assertEqual(sub.failed_charges, MAX_FAILED_CHARGES)
        self.assertEqual(sub.status, SubscriptionStatus.cancelled)
        unsub.assert_awaited_once_with("ord_1")
        notify.assert_awaited_once()
        self.assertTrue(notify.await_args.kwargs["will_cancel"])

    async def test_first_failure_keeps_past_due(self):
        from app.services.billing.subscriptions import handle_failed_recurring

        sub = SimpleNamespace(
            order_id="ord_1",
            user_id="u1",
            status=SubscriptionStatus.active,
            failed_charges=0,
            last_status=None,
            cancelled_at=None,
        )
        user = SimpleNamespace(id="u1")
        db = AsyncMock()
        db.get = AsyncMock(return_value=user)
        db.flush = AsyncMock()

        with (
            patch(
                "app.services.billing.subscriptions.unsubscribe_order",
                AsyncMock(),
            ) as unsub,
            patch(
                "app.services.billing.subscriptions.notify_payment_failed",
                AsyncMock(return_value=True),
            ),
        ):
            result = await handle_failed_recurring(db, sub=sub, status_raw="failure")

        self.assertFalse(result["cancelled"])
        self.assertEqual(sub.failed_charges, 1)
        self.assertEqual(sub.status, SubscriptionStatus.past_due)
        unsub.assert_not_awaited()


class ClaimDailyTests(unittest.IsolatedAsyncioTestCase):
    async def test_claim_once(self):
        from app.services.billing import maintenance as maint

        redis = MagicMock()
        redis.get = AsyncMock(side_effect=[None, "1"])
        redis.setex = AsyncMock()

        with patch.object(maint, "get_redis", AsyncMock(return_value=redis)):
            first = await maint._claim_daily_run()
            second = await maint._claim_daily_run()

        self.assertTrue(first)
        self.assertFalse(second)
        redis.setex.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
