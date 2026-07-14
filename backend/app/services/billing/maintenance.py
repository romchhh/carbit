"""Щоденне обслуговування підписок: expiry + past_due cleanup."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.timezone import as_kyiv, now_kyiv
from app.models.models import BillingSubscription, PlanTier, SubscriptionStatus, User
from app.services.billing.liqpay import unsubscribe_order
from app.services.billing.notify import (
    notify_plan_expired,
    notify_subscription_cancelled,
)
from app.services.billing.plans import enforce_plan_expiry

logger = logging.getLogger(__name__)

# Після скількох невдалих списань підряд скасовуємо рекурент у LiqPay.
MAX_FAILED_CHARGES = 2


async def _claim_daily_run() -> bool:
    """Один прогін на календарний день (Kyiv). Повертає False, якщо вже виконано."""
    day = now_kyiv().strftime("%Y-%m-%d")
    key = f"billing:daily:{day}"
    redis = await get_redis()
    existing = await redis.get(key)
    if existing:
        return False
    await redis.setex(key, 60 * 60 * 36, "1")
    return True


async def expire_paid_plans(db: AsyncSession) -> int:
    """Знімає прострочені платні плани → Free + Telegram."""
    now = now_kyiv()
    rows = (
        await db.scalars(
            select(User).where(
                User.plan != PlanTier.free,
                User.plan_expires_at.is_not(None),
                User.plan_expires_at <= now,
            )
        )
    ).all()

    changed = 0
    for user in rows:
        previous = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
        if not enforce_plan_expiry(user):
            continue
        changed += 1
        try:
            await notify_plan_expired(db, user)
        except Exception:
            logger.exception("notify_plan_expired failed user=%s prev=%s", user.id, previous)
    await db.flush()
    return changed


async def cancel_past_due_subscriptions(db: AsyncSession) -> int:
    """Скасовує past_due після N невдач (якщо callback не встиг unsubscribe)."""
    rows = (
        await db.scalars(
            select(BillingSubscription).where(
                BillingSubscription.status == SubscriptionStatus.past_due,
                BillingSubscription.failed_charges >= MAX_FAILED_CHARGES,
            )
        )
    ).all()

    cancelled = 0
    for sub in rows:
        user = await db.get(User, sub.user_id)
        try:
            await unsubscribe_order(sub.order_id)
        except Exception:
            logger.exception("Daily past_due unsubscribe failed order=%s", sub.order_id)
        sub.status = SubscriptionStatus.cancelled
        sub.cancelled_at = now_kyiv()
        cancelled += 1
        if user:
            try:
                await notify_subscription_cancelled(db, user, reason="past_due")
            except Exception:
                logger.exception("notify cancel past_due failed user=%s", sub.user_id)

    await db.flush()
    return cancelled


async def run_billing_maintenance(db: AsyncSession, *, force: bool = False) -> dict:
    """
    Щоденне обслуговування:
    1) даунгрейд прострочених plan_expires_at
    2) cancel past_due в LiqPay + TG
    """
    if not force and not await _claim_daily_run():
        return {"skipped": True, "reason": "already_ran_today"}

    expired = await expire_paid_plans(db)
    past_due = await cancel_past_due_subscriptions(db)
    logger.info(
        "Billing maintenance done expired=%s past_due_cancelled=%s day=%s",
        expired,
        past_due,
        now_kyiv().strftime("%Y-%m-%d"),
    )
    return {
        "skipped": False,
        "expired_plans": expired,
        "past_due_cancelled": past_due,
        "day": as_kyiv(now_kyiv()).strftime("%Y-%m-%d"),
    }
