from __future__ import annotations

from fastapi import HTTPException

from app.services.auto_ria.client import AutoRiaError

RATE_LIMIT_MESSAGE = "Спробуйте, будь ласка, пізніше"


def raise_auto_ria_http(exc: AutoRiaError) -> None:
    status = exc.status_code or 502
    message = str(exc)

    if "не налаштовано" in message.lower():
        status = 503
    elif "не знайдено" in message.lower():
        status = 400
    elif status == 429:
        message = RATE_LIMIT_MESSAGE

    raise HTTPException(status, message) from exc
