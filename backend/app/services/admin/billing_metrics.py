"""Агрегати LiqPay / підписок для адмінки."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import as_kyiv, now_kyiv
from app.models.models import BillingSubscription, PlanTier, SubscriptionStatus, User
from app.services.billing.plans import get_plan


def serialize_billing_sub(sub: BillingSubscription) -> dict:
    status = sub.status.value if hasattr(sub.status, "value") else str(sub.status)
    plan = get_plan(sub.plan)
    return {
        "id": sub.id,
        "order_id": sub.order_id,
        "plan": sub.plan,
        "plan_name": plan.get("name", sub.plan),
        "amount": int(sub.amount or 0),
        "currency": sub.currency or "UAH",
        "periodicity": sub.periodicity or "month",
        "status": status,
        "last_status": sub.last_status,
        "failed_charges": int(sub.failed_charges or 0),
        "liqpay_payment_id": sub.liqpay_payment_id,
        "card_mask": sub.card_mask,
        "created_at": as_kyiv(sub.created_at).isoformat() if sub.created_at else None,
        "updated_at": as_kyiv(sub.updated_at).isoformat() if sub.updated_at else None,
        "cancelled_at": as_kyiv(sub.cancelled_at).isoformat() if sub.cancelled_at else None,
    }


async def list_user_billing(db: AsyncSession, user_id: str) -> list[dict]:
    rows = (
        await db.scalars(
            select(BillingSubscription)
            .where(BillingSubscription.user_id == user_id)
            .order_by(BillingSubscription.created_at.desc())
        )
    ).all()
    return [serialize_billing_sub(row) for row in rows]


async def count_by_status(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(
        select(BillingSubscription.status, func.count())
        .group_by(BillingSubscription.status)
    )
    out = {s.value: 0 for s in SubscriptionStatus}
    for status, count in result.all():
        key = status.value if hasattr(status, "value") else str(status)
        out[key] = int(count or 0)
    return out


async def recurring_mrr(db: AsyncSession) -> int:
    total = await db.scalar(
        select(func.coalesce(func.sum(BillingSubscription.amount), 0)).where(
            BillingSubscription.status == SubscriptionStatus.active
        )
    )
    return int(total or 0)


async def failed_charges_sum(db: AsyncSession) -> int:
    total = await db.scalar(
        select(func.coalesce(func.sum(BillingSubscription.failed_charges), 0)).where(
            BillingSubscription.status.in_(
                [SubscriptionStatus.past_due, SubscriptionStatus.active]
            )
        )
    )
    return int(total or 0)


async def count_expired_plans(db: AsyncSession) -> int:
    now = now_kyiv()
    return int(
        await db.scalar(
            select(func.count()).select_from(User).where(
                User.plan != PlanTier.free,
                User.plan_expires_at.is_not(None),
                User.plan_expires_at < now,
            )
        )
        or 0
    )


async def count_expiring_soon(db: AsyncSession, *, days: int = 7) -> int:
    now = now_kyiv()
    until = now + timedelta(days=days)
    return int(
        await db.scalar(
            select(func.count()).select_from(User).where(
                User.plan != PlanTier.free,
                User.plan_expires_at.is_not(None),
                User.plan_expires_at >= now,
                User.plan_expires_at <= until,
            )
        )
        or 0
    )


async def billing_overview(db: AsyncSession) -> dict:
    by_status = await count_by_status(db)
    return {
        "by_status": by_status,
        "active_recurring": by_status.get("active", 0),
        "past_due": by_status.get("past_due", 0),
        "failed": by_status.get("failed", 0),
        "cancelled": by_status.get("cancelled", 0),
        "pending": by_status.get("pending", 0),
        "recurring_mrr_uah": await recurring_mrr(db),
        "failed_charges_total": await failed_charges_sum(db),
        "expired_plans": await count_expired_plans(db),
        "expiring_7d": await count_expiring_soon(db, days=7),
    }


async def recent_billing_issues(db: AsyncSession, *, limit: int = 15) -> list[dict]:
    """past_due / failed підписки з ім’ям користувача."""
    rows = (
        await db.execute(
            select(BillingSubscription, User)
            .join(User, User.id == BillingSubscription.user_id)
            .where(
                BillingSubscription.status.in_(
                    [SubscriptionStatus.past_due, SubscriptionStatus.failed]
                )
            )
            .order_by(BillingSubscription.updated_at.desc())
            .limit(limit)
        )
    ).all()
    items = []
    for sub, user in rows:
        item = serialize_billing_sub(sub)
        item["user_id"] = user.id
        item["user_name"] = user.name
        item["user_email"] = user.email
        items.append(item)
    return items
