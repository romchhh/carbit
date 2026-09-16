from __future__ import annotations

from fastapi import HTTPException

# 404 — не знайдено; 410 Gone — оголошення знято з OLX (не помилка парсера).
OLX_GONE_HTTP_STATUS = frozenset({404, 410})


def is_olx_listing_gone(status: int | None) -> bool:
    return status in OLX_GONE_HTTP_STATUS


class OlxError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def raise_olx_http(exc: OlxError) -> None:
    status = exc.status_code or 502
    message = str(exc)

    if "не вдалося" in message.lower() or "тимчасово" in message.lower():
        status = 502
    elif status == 429:
        message = "OLX тимчасово обмежує запити. Спробуйте пізніше."
    elif status == 403:
        message = "OLX тимчасово заблокував запит. Спробуйте через хвилину."

    raise HTTPException(status, message) from exc
