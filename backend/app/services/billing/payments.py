"""Запис історії платежів LiqPay + маска картки."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import as_kyiv, now_kyiv
from app.models.models import BillingPayment, BillingSubscription
from app.services.billing.plans import get_plan


def extract_card_mask(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    for key in (
        "sender_card_mask2",
        "sender_card_mask",
        "card_mask",
        "mask",
        "sender_card",
    ):
        raw = payload.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            # Не зберігати повний номер, якщо LiqPay колись віддав без маски.
            digits = "".join(ch for ch in text if ch.isdigit())
            if len(digits) >= 12 and "*" not in text and "•" not in text and "x" not in text.lower():
                return f"{digits[:6]}******{digits[-4:]}"
            return text
    return None


def _parse_paid_at(payload: dict[str, Any] | None) -> datetime:
    if not payload:
        return now_kyiv()
    for key in ("end_date", "create_date", "completion_date"):
        raw = payload.get(key)
        if raw is None or raw == "":
            continue
        if isinstance(raw, (int, float)):
            ts = float(raw)
            if ts > 1_000_000_000_000:
                ts /= 1000
            try:
                from datetime import UTC, datetime as dt

                return as_kyiv(dt.fromtimestamp(ts, tz=UTC))
            except (OverflowError, OSError, ValueError):
                continue
        text = str(raw).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y %H:%M"):
            try:
                from datetime import datetime as dt

                from app.core.timezone import KYIV_TZ

                return dt.strptime(text[:19], fmt).replace(tzinfo=KYIV_TZ)
            except ValueError:
                continue
        try:
            from datetime import datetime as dt

            return as_kyiv(dt.fromisoformat(text.replace("Z", "+00:00")))
        except ValueError:
            continue
    return now_kyiv()


async def record_billing_payment(
    db: AsyncSession,
    *,
    sub: BillingSubscription,
    payload: dict[str, Any] | None,
    status: str,
) -> BillingPayment:
    mask = extract_card_mask(payload) or sub.card_mask
    payment_id = None
    if payload:
        payment_id = payload.get("payment_id") or payload.get("transaction_id")
    amount = int(sub.amount or 0)
    currency = (sub.currency or "UAH").upper()
    if payload:
        try:
            if payload.get("amount") is not None:
                amount = int(round(float(payload["amount"])))
        except (TypeError, ValueError):
            pass
        if payload.get("currency"):
            currency = str(payload["currency"]).upper()

    plan_name = get_plan(sub.plan).get("name") or sub.plan
    description = None
    if payload and payload.get("description"):
        description = str(payload["description"])[:240]
    else:
        description = f"Підписка Carbit · {plan_name}"

    payment = BillingPayment(
        user_id=sub.user_id,
        subscription_id=sub.id,
        order_id=sub.order_id,
        plan=sub.plan,
        amount=amount,
        currency=currency,
        status=status,
        liqpay_payment_id=str(payment_id) if payment_id else None,
        card_mask=mask,
        description=description,
        paid_at=_parse_paid_at(payload),
    )
    db.add(payment)
    if mask and not sub.card_mask:
        sub.card_mask = mask
    await db.flush()
    return payment


async def list_user_payments(
    db: AsyncSession,
    user_id: str,
    *,
    limit: int = 30,
) -> list[BillingPayment]:
    result = await db.scalars(
        select(BillingPayment)
        .where(BillingPayment.user_id == user_id)
        .order_by(BillingPayment.paid_at.desc())
        .limit(limit)
    )
    return list(result.all())
