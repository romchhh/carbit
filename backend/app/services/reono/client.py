from __future__ import annotations

import asyncio
import logging

import httpx

from app.services.reono.constants import HEADERS, REONO_BASE_URL
from app.services.reono.errors import ReonoError
from app.services.reono.mapper import filters_to_catalog_path
from app.services.reono.parser import parse_catalog_page
from app.schemas.schemas import SearchFilters

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
            await client.get(REONO_BASE_URL)
        except Exception:
            logger.debug("reono warm-up failed", exc_info=True)
        _warmed_up = True


class ReonoClient:
    async def fetch_catalog(self, filters: SearchFilters, *, page: int = 1) -> tuple[list, int]:
        client = await get_shared_http_client()
        await _ensure_warmup(client)
        path = filters_to_catalog_path(filters, page=page)
        url = f"{REONO_BASE_URL}/{path}"
        last_error: Exception | None = None

        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = await client.get(url)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                last_error = ReonoError(f"REONO: мережева помилка: {exc}")
                if attempt + 1 >= _MAX_ATTEMPTS:
                    break
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)])
                continue

            if response.status_code >= 400:
                err = ReonoError(
                    f"REONO: помилка {response.status_code}",
                    status_code=response.status_code,
                )
                if response.status_code in (408, 425, 429, 500, 502, 503, 504) and attempt + 1 < _MAX_ATTEMPTS:
                    last_error = err
                    await asyncio.sleep(_RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)])
                    continue
                raise err

            cars, total = parse_catalog_page(response.text)
            return cars, total

        raise last_error or ReonoError("REONO: невідома помилка")
