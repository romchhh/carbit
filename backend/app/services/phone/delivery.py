"""Доставка кодів підтвердження телефону (SMS або Telegram)."""

from __future__ import annotations

import logging

from app.models.models import User
from app.services.sms.turbosms import TurboSmsError, send_verification_code as send_sms_code
from app.services.telegram.client import telegram_client

logger = logging.getLogger(__name__)


class PhoneCodeDeliveryError(RuntimeError):
    pass


async def deliver_phone_auth_code(
    *,
    phone: str,
    code: str,
    intent: str,
    user: User | None,
    delivery: str = "auto",
) -> tuple[str, str]:
    """Повертає (message, channel) де channel = sms | telegram."""
    force_sms = intent == "register" or delivery == "sms"

    if not force_sms and user and user.telegram_connected and user.telegram_id:
        text = (
            f"🔐 Carbit: ваш код входу <b>{code}</b>.\n"
            "Нікому не повідомляйте його."
        )
        result = await telegram_client.send_message(user.telegram_id, text)
        if result and result.get("ok"):
            return "Код надіслано в Telegram", "telegram"
        logger.warning("Telegram auth code failed for %s, falling back to SMS", phone)

    try:
        await send_sms_code(phone=phone, code=code)
    except TurboSmsError as exc:
        raise PhoneCodeDeliveryError(str(exc)) from exc

    return "Код підтвердження надіслано SMS", "sms"
