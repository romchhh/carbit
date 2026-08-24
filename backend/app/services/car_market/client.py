from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.services.car_market.constants import (
    CAR_MARKET_BASE_URL,
    CAR_MARKET_CATALOG_URL,
    HEADERS,
)
from app.services.car_market.errors import CarMarketError
from app.services.car_market.parser import parse_catalog_page
from app.services.search.source_error import http_request_label

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 2
_RETRY_BACKOFF_SECONDS = (0.3, 0.8)

_http_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()
_warmed_up = False
_warmup_lock = asyncio.Lock()


async def get_shared_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        return _http_client

    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=20.0,
                headers=HEADERS,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=12, max_keepalive_connections=6),
            )
        return _http_client


async def _ensure_warmup(client: httpx.AsyncClient) -> None:
    global _warmed_up
    if _warmed_up:
        return
    async with _warmup_lock:
        if _warmed_up:
            return
        try:
            await client.get(CAR_MARKET_BASE_URL)
        except Exception:
            logger.debug("car-market warm-up failed", exc_info=True)
        _warmed_up = True


class CarMarketClient:
    async def fetch_catalog(self, params: dict[str, Any]) -> tuple[list, int]:
        client = await get_shared_http_client()
        await _ensure_warmup(client)
        last_error: Exception | None = None

        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = await client.get(CAR_MARKET_CATALOG_URL, params=params)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                request_label = http_request_label("GET", CAR_MARKET_CATALOG_URL, params=params)
                last_error = CarMarketError(
                    f"Car Market: мережева помилка: {exc}",
                    request=request_label,
                )
                if attempt + 1 >= _MAX_ATTEMPTS:
                    break
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)])
                continue

            request_label = http_request_label("GET", str(response.url))
            if response.status_code >= 400:
                err = CarMarketError(
                    f"Car Market: помилка {response.status_code}",
                    status_code=response.status_code,
                    request=request_label,
                )
                if response.status_code in (408, 425, 429, 500, 502, 503, 504) and attempt + 1 < _MAX_ATTEMPTS:
                    last_error = err
                    await asyncio.sleep(_RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)])
                    continue
                raise err

            cars, total = parse_catalog_page(response.text)
            return cars, total

        raise last_error or CarMarketError(
            "Car Market: невідома помилка",
            request=http_request_label("GET", CAR_MARKET_CATALOG_URL, params=params),
        )
