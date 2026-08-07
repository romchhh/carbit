"""Відправка SMS через TurboSMS (turbosms.ua)."""

from __future__ import annotations

import logging
import re

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TURBOSMS_API_URL = "https://api.turbosms.ua/message/send.json"
SENDER_PATTERN = re.compile(r"^[A-Za-z0-9 ._&-]{3,11}$")


class TurboSmsError(RuntimeError):
    pass


def resolve_sms_sender() -> str:
    sender = (settings.TURBOSMS_SENDER or "Carbit").strip()
    if not SENDER_PATTERN.fullmatch(sender):
        raise TurboSmsError(
            f"Невірне ім'я відправника SMS «{sender}». "
            "У .env вкажіть TURBOSMS_SENDER=Carbit (3–11 латинських символів, як у кабінеті TurboSMS).",
        )
    return sender


async def send_sms(*, phone: str, text: str) -> None:
    token = (settings.TURBOSMS_TOKEN or "").strip()
    sender = resolve_sms_sender()

    if not token:
        if settings.DEBUG:
            logger.warning("TurboSMS disabled — SMS to %s: %s", phone, text)
            return
        raise TurboSmsError("SMS-сервіс не налаштовано")

    payload = {
        "recipients": [phone],
        "sms": {
            "sender": sender,
            "text": text,
        },
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(TURBOSMS_API_URL, json=payload, headers=headers)

    try:
        data = response.json()
    except ValueError as exc:
        raise TurboSmsError("Некоректна відповідь TurboSMS") from exc

    if response.status_code != 200:
        message = data.get("response_status") or data.get("message") or response.text
        raise TurboSmsError(str(message))

    result = data.get("response_result")
    if isinstance(result, list) and result:
        first = result[0]
        code = int(first.get("response_code") or 0)
        if code not in (0, 800, 801, 802, 803):
            raise TurboSmsError(str(first.get("response_status") or "Помилка відправки SMS"))

    response_code = int(data.get("response_code") or 0)
    if response_code not in (0, 800, 801, 802, 803):
        raise TurboSmsError(str(data.get("response_status") or "Помилка відправки SMS"))


async def send_verification_code(*, phone: str, code: str) -> None:
    text = f"Ваш код підтвердження {code}. Нікому не повідомляйте його."
    await send_sms(phone=phone, text=text)
