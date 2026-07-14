"""Створення checkout LiqPay + обробка callback."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.timezone import now_kyiv
from app.models.models import BillingSubscription, SubscriptionStatus, User
from app.services.billing.liqpay import (
    LIQPAY_CHECKOUT_URL,
    SUCCESS_STATUSES,
    LiqPayNotConfiguredError,
    decode_data,
    encode_checkout,
    liqpay_configured,
    unsubscribe_order,
    verify_callback,
)
from app.services.billing.notify import (
    notify_payment_failed,
    notify_plan_activated,
    notify_subscription_cancelled,
)
from app.services.billing.plans import activate_plan, get_plan
from app.services.billing.maintenance import MAX_FAILED_CHARGES

logger = logging.getLogger(__name__)


def make_order_id(user_id: str, plan_id: str) -> str:
    short = uuid.uuid4().hex[:10]
    return f"carbit_{plan_id}_{user_id[:8]}_{short}"


async def get_active_subscription(
    db: AsyncSession,
    user_id: str,
) -> BillingSubscription | None:
    result = await db.scalars(
        select(BillingSubscription)
        .where(
            BillingSubscription.user_id == user_id,
            BillingSubscription.status == SubscriptionStatus.active,
        )
        .order_by(BillingSubscription.created_at.desc())
    )
    return result.first()


async def create_checkout(
    db: AsyncSession,
    user: User,
    plan_id: str,
) -> dict:
    if not liqpay_configured():
        raise LiqPayNotConfiguredError("LiqPay не налаштовано")
    if plan_id == "free":
        raise ValueError("Free план не потребує оплати")
    plan = get_plan(plan_id)
    amount = int(plan.get("price_uah") or 0)
    if amount <= 0:
        raise ValueError("Невідомий або безкоштовний план")

    order_id = make_order_id(user.id, plan_id)
    start = now_kyiv().strftime("%Y-%m-%d %H:%M:%S")
    api_base = settings.PUBLIC_API_BASE.rstrip("/")
    frontend = settings.FRONTEND_URL.rstrip("/")

    # Client-Server Checkout: action=pay + subscribe=1 (не server-server action=subscribe).
    # Інакше LiqPay інколи віддає 403 на кроці /checkout/card/...
    params: dict = {
        "action": "pay",
        "amount": amount,
        "currency": "UAH",
        "description": f"Carbit: тариф {plan['name']} (щомісячна підписка)",
        "order_id": order_id,
        "subscribe": "1",
        "subscribe_date_start": start,
        "subscribe_periodicity": "month",
        "server_url": f"{api_base}/billing/liqpay/callback",
        "result_url": f"{frontend}/app/billing?paid=1",
        "language": "uk",
    }
    if settings.LIQPAY_PUBLIC_KEY.strip().startswith("sandbox_"):
        params["sandbox"] = 1
    data, signature = encode_checkout(params)

    sub = BillingSubscription(
        order_id=order_id,
        user_id=user.id,
        plan=plan_id,
        amount=amount,
        currency="UAH",
        periodicity="month",
        status=SubscriptionStatus.pending,
    )
    db.add(sub)
    await db.flush()

    return {
        "order_id": order_id,
        "checkout_url": LIQPAY_CHECKOUT_URL,
        "data": data,
        "signature": signature,
        "amount": amount,
        "currency": "UAH",
        "plan": plan_id,
        "plan_name": plan["name"],
    }


async def cancel_active_subscriptions(db: AsyncSession, user_id: str) -> None:
    result = await db.scalars(
        select(BillingSubscription).where(
            BillingSubscription.user_id == user_id,
            BillingSubscription.status.in_(
                [
                    SubscriptionStatus.active,
                    SubscriptionStatus.pending,
                    SubscriptionStatus.past_due,
                ]
            ),
        )
    )
    now = now_kyiv()
    for sub in result.all():
        if sub.status in (SubscriptionStatus.active, SubscriptionStatus.past_due):
            try:
                await unsubscribe_order(sub.order_id)
            except Exception:
                logger.exception("LiqPay unsubscribe failed for %s", sub.order_id)
        sub.status = SubscriptionStatus.cancelled
        sub.cancelled_at = now


async def apply_successful_payment(
    db: AsyncSession,
    *,
    sub: BillingSubscription,
    payload: dict,
) -> None:
    user = await db.get(User, sub.user_id)
    if not user:
        logger.error("LiqPay callback: user missing for %s", sub.order_id)
        return

    previous_plan = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    status_raw = str(payload.get("status") or "")
    card_token = payload.get("card_token") or payload.get("token")
    payment_id = payload.get("payment_id") or payload.get("transaction_id")

    # Інші активні підписки цього юзера скасовуємо в LiqPay
    others = await db.scalars(
        select(BillingSubscription).where(
            BillingSubscription.user_id == user.id,
            BillingSubscription.id != sub.id,
            BillingSubscription.status == SubscriptionStatus.active,
        )
    )
    for other in others.all():
        try:
            await unsubscribe_order(other.order_id)
        except Exception:
            logger.exception("Failed to unsubscribe previous %s", other.order_id)
        other.status = SubscriptionStatus.cancelled
        other.cancelled_at = now_kyiv()

    was_active = sub.status == SubscriptionStatus.active
    sub.status = SubscriptionStatus.active
    sub.last_status = status_raw
    sub.failed_charges = 0
    if card_token:
        sub.card_token = str(card_token)
    if payment_id:
        sub.liqpay_payment_id = str(payment_id)

    activate_plan(user, sub.plan)
    # Рекурентне списання → продовжити ще на period_days від зараз
    if was_active and previous_plan == sub.plan:
        days = int(get_plan(sub.plan).get("period_days") or 30)
        user.plan_expires_at = now_kyiv() + timedelta(days=days)

    await db.flush()
    if not was_active or previous_plan != sub.plan:
        await notify_plan_activated(db, user, previous_plan=previous_plan)


async def handle_failed_recurring(
    db: AsyncSession,
    *,
    sub: BillingSubscription,
    status_raw: str,
) -> dict:
    """Невдале списання: лічильник → після N спроб unsubscribe + TG."""
    user = await db.get(User, sub.user_id)
    sub.last_status = status_raw
    sub.failed_charges = int(sub.failed_charges or 0) + 1
    attempt = sub.failed_charges
    will_cancel = attempt >= MAX_FAILED_CHARGES

    if sub.status != SubscriptionStatus.active and sub.status != SubscriptionStatus.past_due:
        # pending checkout failure
        sub.status = SubscriptionStatus.failed
        await db.flush()
        return {"ok": True, "status": status_raw, "failed_charges": attempt, "cancelled": False}

    sub.status = SubscriptionStatus.past_due

    if will_cancel:
        try:
            await unsubscribe_order(sub.order_id)
        except Exception:
            logger.exception("Auto-unsubscribe after failed charge order=%s", sub.order_id)
        sub.status = SubscriptionStatus.cancelled
        sub.cancelled_at = now_kyiv()

    await db.flush()

    if user:
        try:
            await notify_payment_failed(
                db,
                user,
                attempt=attempt,
                max_attempts=MAX_FAILED_CHARGES,
                will_cancel=will_cancel,
            )
        except Exception:
            logger.exception("notify_payment_failed user=%s", sub.user_id)

    return {
        "ok": True,
        "status": status_raw,
        "failed_charges": attempt,
        "cancelled": will_cancel,
    }


async def handle_callback(db: AsyncSession, data: str, signature: str) -> dict:
    if not verify_callback(data, signature):
        raise ValueError("Invalid LiqPay signature")

    payload = decode_data(data)
    order_id = str(payload.get("order_id") or "")
    status_raw = str(payload.get("status") or "").lower()
    if not order_id:
        raise ValueError("Missing order_id")

    sub = await db.scalar(
        select(BillingSubscription).where(BillingSubscription.order_id == order_id)
    )
    if not sub:
        logger.warning("LiqPay callback for unknown order_id=%s", order_id)
        return {"ok": False, "reason": "unknown_order"}

    sub.last_status = status_raw

    if status_raw in SUCCESS_STATUSES:
        await apply_successful_payment(db, sub=sub, payload=payload)
        return {"ok": True, "status": status_raw, "order_id": order_id}

    if status_raw in {"failure", "error", "reversed", "expired"}:
        return await handle_failed_recurring(db, sub=sub, status_raw=status_raw)

    if status_raw == "unsubscribed":
        already_cancelled = sub.status == SubscriptionStatus.cancelled
        sub.status = SubscriptionStatus.cancelled
        sub.cancelled_at = sub.cancelled_at or now_kyiv()
        await db.flush()
        if not already_cancelled:
            user = await db.get(User, sub.user_id)
            if user:
                try:
                    await notify_subscription_cancelled(db, user, reason="user")
                except Exception:
                    logger.exception("notify unsubscribed callback user=%s", sub.user_id)
        return {"ok": True, "status": status_raw, "order_id": order_id}

    await db.flush()
    return {"ok": True, "status": status_raw, "order_id": order_id, "ignored": True}
