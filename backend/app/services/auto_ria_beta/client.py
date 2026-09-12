from __future__ import annotations

import asyncio
import logging

import httpx

from app.services.auto_ria_beta.constants import (
    CATEGORY_LEGKOVI,
    HEADERS,
    MARKS_API,
    REQUEST_DELAY_SECONDS,
    SEARCH_URL,
)
from app.services.auto_ria_beta.errors import AutoRiaBetaError
from app.services.auto_ria_beta.parser import parse_listing_details, parse_search_page
from app.services.search.http_proxy import (
    html_response_blocked,
    httpx_proxy_kwargs,
    proxy_configured,
    resolve_search_proxy_url,
)
from app.services.search.source_error import http_request_label

logger = logging.getLogger(__name__)

_direct_client: httpx.AsyncClient | None = None
_proxy_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()
# Після першої відповіді 200 — лише цей шлях. Без очікування фейлу.
_html_route: str | None = None


def _client_kwargs(proxy: str | None = None) -> dict:
    return {
        "timeout": 25.0,
        "headers": HEADERS,
        "follow_redirects": True,
        "limits": httpx.Limits(max_connections=12, max_keepalive_connections=6),
        **httpx_proxy_kwargs(proxy),
    }


def _html_ok(response: httpx.Response | None) -> bool:
    return bool(
        response is not None
        and response.status_code == 200
        and not html_response_blocked(response.status_code, response.text)
    )


async def _fetch_html(
    client: httpx.AsyncClient,
    url: str,
    params: dict | None,
) -> httpx.Response | None:
    try:
        response = await client.get(url, params=params)
    except httpx.HTTPError:
        return None
    return response if _html_ok(response) else None


async def _get_direct_client() -> httpx.AsyncClient:
    global _direct_client
    if _direct_client is not None and not _direct_client.is_closed:
        return _direct_client
    async with _client_lock:
        if _direct_client is None or _direct_client.is_closed:
            _direct_client = httpx.AsyncClient(**_client_kwargs())
        return _direct_client


async def _get_proxy_client() -> httpx.AsyncClient | None:
    global _proxy_client
    if not proxy_configured():
        return None
    if _proxy_client is not None and not _proxy_client.is_closed:
        return _proxy_client
    async with _client_lock:
        if _proxy_client is not None and not _proxy_client.is_closed:
            return _proxy_client
        proxy = await resolve_search_proxy_url(sticky=True)
        if not proxy:
            return None
        _proxy_client = httpx.AsyncClient(**_client_kwargs(proxy))
        return _proxy_client


async def _get_html(url: str, *, params: dict | None = None) -> httpx.Response:
    """Проксі не додає очікування: гонка з direct, далі лише переможець."""
    global _html_route
    request_label = http_request_label("GET", url, params=params)

    if _html_route == "direct":
        response = await _fetch_html(await _get_direct_client(), url, params)
        if response is not None:
            return response
        _html_route = None
    elif _html_route == "proxy":
        proxy_client = await _get_proxy_client()
        if proxy_client is None:
            raise AutoRiaBetaError(
                "AUTO.RIA HTML blocked and proxy is not configured",
                request=request_label,
            )
        response = await _fetch_html(proxy_client, url, params)
        if response is not None:
            return response
        from app.services.search.proxy_alerts import schedule_proxy_problem

        schedule_proxy_problem(source="AUTO.RIA", error="проксі не віддав HTML")
        raise AutoRiaBetaError("AUTO.RIA HTML proxy failed", request=request_label)

    if not proxy_configured():
        response = await _fetch_html(await _get_direct_client(), url, params)
        if response is None:
            raise AutoRiaBetaError("AUTO.RIA HTML failed", request=request_label)
        _html_route = "direct"
        return response

    async def _direct_leg() -> tuple[str, httpx.Response | None]:
        return "direct", await _fetch_html(await _get_direct_client(), url, params)

    async def _proxy_leg() -> tuple[str, httpx.Response | None]:
        proxy_client = await _get_proxy_client()
        if proxy_client is None:
            return "proxy", None
        return "proxy", await _fetch_html(proxy_client, url, params)

    tasks = [
        asyncio.create_task(_direct_leg()),
        asyncio.create_task(_proxy_leg()),
    ]
    pending: set[asyncio.Task] = set(tasks)
    try:
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if task.cancelled() or task.exception() is not None:
                    continue
                name, response = task.result()
                if response is None:
                    continue
                _html_route = name
                for leftover in pending:
                    leftover.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
                logger.info("AUTO.RIA HTML via %s", name)
                return response
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()

    from app.services.search.proxy_alerts import schedule_proxy_problem

    schedule_proxy_problem(source="AUTO.RIA", error="direct і проксі не віддали HTML")
    raise AutoRiaBetaError("AUTO.RIA HTML failed", request=request_label)


class AutoRiaBetaClient:
    async def resolve_brand_id(self, brand_name: str) -> int:
        key = brand_name.strip().lower()
        try:
            client = await _get_direct_client()
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
        response = await _get_html(SEARCH_URL, params=params)
        await asyncio.sleep(REQUEST_DELAY_SECONDS)
        cars, total = parse_search_page(response.text)
        return cars, total

    async def fetch_listing_html(self, url: str) -> str:
        response = await _get_html(url)
        await asyncio.sleep(REQUEST_DELAY_SECONDS)
        return response.text

    async def enrich_car(self, car) -> None:
        html = await self.fetch_listing_html(car.url)
        car.details = parse_listing_details(html, car)
