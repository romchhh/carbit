from __future__ import annotations

from fastapi import HTTPException

from app.services.auto_ria.client import AutoRiaError

RATE_LIMIT_MESSAGE = "Спробуйте, будь ласка, пізніше"


def raise_auto_ria_http(exc: AutoRiaError) -> None:
    status = exc.status_code or 502
    message = str(exc)

    if "не налаштовано" in message.lower():
        status = 503
        message = "AUTO.RIA не налаштовано на сервері. Додайте AUTO_RIA_API_KEY у .env і перезберіть backend."
    elif "не знайдено" in message.lower():
        status = 400
    elif status == 403:
        message = "Невалідний ключ AUTO.RIA. Перевірте AUTO_RIA_API_KEY у .env."
    elif status == 404:
        status = 502
        raw = str(exc).lower()
        if "httpoison" in raw or ":closed" in raw:
            message = "AUTO.RIA тимчасово обірвав з'єднання. Спробуйте ще раз."
        else:
            message = "AUTO.RIA тимчасово недоступний. Спробуйте пізніше."
    elif status in (500, 502, 503, 504):
        status = 502
        message = "AUTO.RIA тимчасово недоступний. Спробуйте пізніше."
    elif status == 429:
        message = RATE_LIMIT_MESSAGE

    raise HTTPException(status, message) from exc
