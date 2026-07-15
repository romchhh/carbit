from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.services.baza_gai.errors import (
    BazaGaiError,
    BazaGaiNotConfigured,
    BazaGaiNotFound,
    BazaGaiRateLimited,
)

_TIMEOUT = httpx.Timeout(20.0)


class BazaGaiClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = (api_key if api_key is not None else settings.BAZA_GAI_API_KEY).strip()
        self.base_url = (base_url or settings.BAZA_GAI_BASE_URL).rstrip("/")
        if not self.api_key:
            raise BazaGaiNotConfigured()

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "X-Api-Key": self.api_key,
        }

    async def get_json(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, headers=self._headers())

        if response.status_code == 404:
            raise BazaGaiNotFound(path.rsplit("/", 1)[-1])
        if response.status_code == 429:
            raise BazaGaiRateLimited()
        if response.status_code in (401, 403):
            raise BazaGaiError("Невірний або відхилений API-ключ Бази ДАІ", status_code=503)
        if response.status_code >= 400:
            raise BazaGaiError(
                f"База ДАІ помилка {response.status_code}",
                status_code=502,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise BazaGaiError("База ДАІ повернула некоректну відповідь", status_code=502) from exc

        if isinstance(data, dict) and data.get("error"):
            message = str(data.get("error") or data.get("message") or "Помилка Бази ДАІ")
            raise BazaGaiError(message, status_code=502)

        return data

    async def lookup_vin(self, vin: str) -> dict[str, Any]:
        data = await self.get_json(f"/vin/{vin}")
        if not isinstance(data, dict):
            raise BazaGaiError("Неочікувана відповідь /vin", status_code=502)
        # Порожня відповідь без операцій / марки — як «не знайдено»
        if not data.get("operations") and not data.get("vendor") and not data.get("digits"):
            raise BazaGaiNotFound(vin)
        return data
