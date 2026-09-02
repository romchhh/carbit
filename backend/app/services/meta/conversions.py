"""Meta (Facebook) Conversions API — серверні події для реклами."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_GRAPH_API_VERSION = "v21.0"


def meta_conversions_configured() -> bool:
    return bool(
        (settings.META_PIXEL_ID or "").strip()
        and (settings.META_CONVERSIONS_ACCESS_TOKEN or "").strip()
    )


def _hash_meta(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    if digits.startswith("0"):
        digits = f"38{digits}"
    elif not digits.startswith("38"):
        digits = f"38{digits}"
    return digits


def build_purchase_event_id(*, order_id: str, payment_id: str | None = None) -> str:
    if payment_id:
        return f"purchase_{payment_id}"
    return f"purchase_{order_id}"


def build_purchase_event(
    *,
    user_id: str,
    email: str | None,
    phone: str | None,
    order_id: str,
    payment_id: str | None,
    plan_id: str,
    plan_name: str,
    amount: float,
    currency: str,
    event_time: int | None = None,
) -> dict[str, Any]:
    user_data: dict[str, list[str]] = {
        "external_id": [_hash_meta(user_id)],
    }
    if email:
        user_data["em"] = [_hash_meta(email)]
    normalized_phone = _normalize_phone(phone)
    if normalized_phone:
        user_data["ph"] = [_hash_meta(normalized_phone)]

    value = round(max(float(amount), 0.0), 2)
    code = (currency or "UAH").upper()

    return {
        "event_name": "Purchase",
        "event_time": int(event_time or time.time()),
        "event_id": build_purchase_event_id(order_id=order_id, payment_id=payment_id),
        "action_source": "website",
        "user_data": user_data,
        "custom_data": {
            "currency": code,
            "value": value,
            "content_type": "product",
            "content_ids": [plan_id],
            "content_name": plan_name,
            "order_id": order_id,
        },
    }


async def send_meta_purchase_event(
    *,
    user_id: str,
    email: str | None,
    phone: str | None,
    order_id: str,
    payment_id: str | None,
    plan_id: str,
    plan_name: str,
    amount: float,
    currency: str,
) -> bool:
    if not meta_conversions_configured():
        return False

    pixel_id = settings.META_PIXEL_ID.strip()
    token = settings.META_CONVERSIONS_ACCESS_TOKEN.strip()
    event = build_purchase_event(
        user_id=user_id,
        email=email,
        phone=phone,
        order_id=order_id,
        payment_id=payment_id,
        plan_id=plan_id,
        plan_name=plan_name,
        amount=amount,
        currency=currency,
    )
    url = f"https://graph.facebook.com/{_GRAPH_API_VERSION}/{pixel_id}/events"
    payload = {"data": [event], "access_token": token}

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(url, json=payload)
        if response.status_code >= 400:
            logger.warning(
                "Meta Purchase event failed status=%s body=%s",
                response.status_code,
                response.text[:500],
            )
            return False
        logger.info(
            "Meta Purchase event sent order_id=%s event_id=%s",
            order_id,
            event["event_id"],
        )
        return True
    except Exception:
        logger.exception("Meta Purchase event request failed order_id=%s", order_id)
        return False


def schedule_meta_purchase_event(
    *,
    user_id: str,
    email: str | None,
    phone: str | None,
    order_id: str,
    payment_id: str | None,
    plan_id: str,
    plan_name: str,
    amount: float,
    currency: str,
) -> None:
    """Fire-and-forget після успішної оплати (не блокує LiqPay callback)."""
    if not meta_conversions_configured():
        return

    async def _run() -> None:
        await send_meta_purchase_event(
            user_id=user_id,
            email=email,
            phone=phone,
            order_id=order_id,
            payment_id=payment_id,
            plan_id=plan_id,
            plan_name=plan_name,
            amount=amount,
            currency=currency,
        )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("Meta Purchase skipped: no running event loop")
        return
    loop.create_task(_run())
