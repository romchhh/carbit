from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.services.imperiya.constants import IMPERIYA_API_BASE_URL
from app.services.imperiya.errors import ImperiyaError
from app.services.search.source_error import http_request_label

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (0.4, 1.0, 2.0)

_http_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def get_shared_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        return _http_client

    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=25.0,
                base_url=IMPERIYA_API_BASE_URL,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return _http_client


class ImperiyaClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or settings.IMPERIYA_API_KEY or "").strip()
        if not self.api_key:
            raise ImperiyaError("IMPERIYA_API_KEY не налаштовано")

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        headers = {"X-API-Key": self.api_key, "Accept": "application/json"}
        last_error: Exception | None = None

        for attempt in range(_MAX_ATTEMPTS):
            request_label = http_request_label(
                "GET",
                f"{IMPERIYA_API_BASE_URL}{path}",
                params=params,
            )
            try:
                client = await get_shared_http_client()
                response = await client.get(path, params=params, headers=headers)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                last_error = ImperiyaError(
                    f"Імперія Авто: мережева помилка: {exc}",
                    request=request_label,
                )
                if attempt + 1 >= _MAX_ATTEMPTS:
                    break
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)])
                continue

            if response.status_code >= 400:
                body = response.text[:200]
                err = ImperiyaError(
                    f"Імперія Авто: помилка {response.status_code}: {body}",
                    response.status_code,
                    request=request_label,
                )
                if response.status_code in (408, 425, 429, 500, 502, 503, 504, 522) and attempt + 1 < _MAX_ATTEMPTS:
                    await asyncio.sleep(_RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)])
                    last_error = err
                    continue
                raise err

            try:
                return response.json()
            except ValueError as exc:
                raise ImperiyaError("Імперія Авто: некоректна JSON-відповідь") from exc

        raise last_error or ImperiyaError("Імперія Авто: невідома помилка")

    async def search_cars(self, params: dict[str, Any]) -> dict[str, Any]:
        data = await self.get("/api/v2/cars", params=params)
        if not isinstance(data, dict):
            raise ImperiyaError("Імперія Авто: очікувався об'єкт зі списком оголошень")
        return data

    async def get_car(self, car_id: int | str) -> dict[str, Any]:
        data = await self.get(f"/api/v2/cars/{car_id}")
        if not isinstance(data, dict):
            raise ImperiyaError("Імперія Авто: очікувався об'єкт оголошення")
        return data

    async def list_makes(self) -> list[dict[str, Any]]:
        data = await self.get("/api/v2/references/makes")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        raise ImperiyaError("Імперія Авто: некоректний список марок")

    async def list_models(self, make_id: int) -> list[dict[str, Any]]:
        data = await self.get(f"/api/v2/references/makes/{make_id}/models")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        raise ImperiyaError("Імперія Авто: некоректний список моделей")

    async def list_regions(self) -> list[dict[str, Any]]:
        data = await self.get("/api/v2/references/regions")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        raise ImperiyaError("Імперія Авто: некоректний список регіонів")
