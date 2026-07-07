from __future__ import annotations

from fastapi import HTTPException


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

    raise HTTPException(status, message) from exc
