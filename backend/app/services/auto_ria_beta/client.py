from __future__ import annotations

import asyncio
import logging

import httpx

from app.services.auto_ria_beta.constants import (
    BASE_URL,
    CATEGORY_LEGKOVI,
    HEADERS,
    MARKS_API,
    REQUEST_DELAY_SECONDS,
    SEARCH_URL,
)
from app.services.auto_ria_beta.errors import AutoRiaBetaError
from app.services.auto_ria_beta.parser import parse_listing_details, parse_search_page
from app.services.search.source_error import http_request_label

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()
_warmed_up = False


async def get_shared_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        return _http_client

    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=25.0,
                headers=HEADERS,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=12, max_keepalive_connections=6),
            )
        return _http_client


async def _ensure_warmup(client: httpx.AsyncClient) -> None:
    global _warmed_up
    if _warmed_up:
        return
    async with _client_lock:
        if _warmed_up:
            return
        try:
            await client.get(BASE_URL)
        except Exception:
            logger.debug("auto_ria_beta warm-up failed", exc_info=True)
        _warmed_up = True


class AutoRiaBetaClient:
    async def resolve_brand_id(self, brand_name: str) -> int:
        key = brand_name.strip().lower()
        try:
            client = await get_shared_http_client()
            url = MARKS_API.format(category_id=CATEGORY_LEGKOVI)
            response = await client.get(url)
            response.raise_for_status()
            marks = response.json()
            for mark in marks:
                if str(mark.get("name", "")).strip().lower() == key:
                    return int(mark["value"])
        except Exception as exc:
            raise AutoRiaBetaError(
                f"Не вдалось визначити ID марки '{brand_name}': {exc}",
                request=MARKS_API.format(category_id=CATEGORY_LEGKOVI),
            ) from exc
        raise AutoRiaBetaError(f"Марку '{brand_name}' не знайдено в каталозі AUTO.RIA")

    async def fetch_search_page(self, params: dict) -> tuple[list, int]:
        client = await get_shared_http_client()
        await _ensure_warmup(client)
        request_label = http_request_label("GET", SEARCH_URL, params=params)
        try:
            response = await client.get(SEARCH_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AutoRiaBetaError(f"AUTO.RIA HTML search failed: {exc}", request=request_label) from exc

        await asyncio.sleep(REQUEST_DELAY_SECONDS)
        cars, total = parse_search_page(response.text)
        return cars, total

    async def fetch_listing_html(self, url: str) -> str:
        client = await get_shared_http_client()
        await _ensure_warmup(client)
        request_label = http_request_label("GET", url)
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AutoRiaBetaError(f"AUTO.RIA HTML details failed: {exc}", request=request_label) from exc
        await asyncio.sleep(REQUEST_DELAY_SECONDS)
        return response.text

    async def enrich_car(self, car) -> None:
        html = await self.fetch_listing_html(car.url)
        car.details = parse_listing_details(html, car)
