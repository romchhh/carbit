"""LiqPay client: checkout signing + callback verify + API calls."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

LIQPAY_CHECKOUT_URL = "https://www.liqpay.ua/api/3/checkout"
LIQPAY_API_URL = "https://www.liqpay.ua/api/request"

# Статуси, які вважаємо успішною оплатою / активною підпискою
SUCCESS_STATUSES = frozenset(
    {
        "success",
        "subscribed",
        "sandbox",
        "wait_accept",  # sandbox
    }
)


class LiqPayNotConfiguredError(RuntimeError):
    pass


def liqpay_configured() -> bool:
    return bool(settings.LIQPAY_PUBLIC_KEY.strip() and settings.LIQPAY_PRIVATE_KEY.strip())


def _require_keys() -> tuple[str, str]:
    public = settings.LIQPAY_PUBLIC_KEY.strip()
    private = settings.LIQPAY_PRIVATE_KEY.strip()
    if not public or not private:
        raise LiqPayNotConfiguredError("LiqPay ключі не налаштовані")
    return public, private


def _encode_data(params: dict[str, Any]) -> str:
    raw = json.dumps(params, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _sign(data: str, *, algo: str = "sha1") -> str:
    _, private = _require_keys()
    payload = f"{private}{data}{private}".encode("utf-8")
    if algo == "sha3-256":
        digest = hashlib.sha3_256(payload).digest()
    else:
        digest = hashlib.sha1(payload).digest()
    return base64.b64encode(digest).decode("ascii")


def encode_checkout(params: dict[str, Any]) -> tuple[str, str]:
    """Повертає (data, signature) для HTML-форми Checkout."""
    public, _ = _require_keys()
    payload = {"public_key": public, "version": 3, **params}
    data = _encode_data(payload)
    # Класичний API/Checkout subscribe — sha1
    signature = _sign(data, algo="sha1")
    return data, signature


def verify_callback(data: str, signature: str) -> bool:
    """Перевірка підпису callback (sha1 або sha3-256)."""
    if not data or not signature:
        return False
    try:
        _require_keys()
    except LiqPayNotConfiguredError:
        return False
    expected_sha1 = _sign(data, algo="sha1")
    if expected_sha1 == signature:
        return True
    expected_sha3 = _sign(data, algo="sha3-256")
    return expected_sha3 == signature


def decode_data(data: str) -> dict[str, Any]:
    raw = base64.b64decode(data.encode("ascii"))
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Invalid LiqPay data payload")
    return payload


async def api_request(params: dict[str, Any]) -> dict[str, Any]:
    public, _ = _require_keys()
    payload = {"public_key": public, "version": 3, **params}
    data = _encode_data(payload)
    signature = _sign(data, algo="sha1")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            LIQPAY_API_URL,
            data={"data": data, "signature": signature},
        )
        resp.raise_for_status()
        body = resp.json()
        if not isinstance(body, dict):
            return {"raw": body}
        return body


async def unsubscribe_order(order_id: str) -> dict[str, Any]:
    return await api_request({"action": "unsubscribe", "order_id": order_id})


async def status_order(order_id: str) -> dict[str, Any]:
    return await api_request({"action": "status", "order_id": order_id})
