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
# Після успішного direct — лише direct (не палимо Webshare).
# proxy — лише якщо direct був заблокований.
_html_route: str | None = None
_PROXY_YIELD_TO_DIRECT_SECONDS = 0.45


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


async def _reset_proxy_client() -> None:
    global _proxy_client
    from app.services.search.http_proxy import invalidate_sticky_proxy

    invalidate_sticky_proxy()
    if _proxy_client is None:
        return
    try:
        await _proxy_client.aclose()
    except Exception:
        pass
    _proxy_client = None


def _alert_html_failed() -> None:
    logger.warning("AUTO.RIA HTML unavailable: direct and proxy returned no usable HTML")


async def _retry_html_fetch(
    *,
    try_direct,
    try_proxy,
) -> httpx.Response | None:
    """Одна повторна спроба після збою direct+proxy перед адмін-алертом."""
    global _html_route

    _html_route = None
    await _reset_proxy_client()
    await asyncio.sleep(0.5)
    response = await try_direct()
    if response is not None:
        _html_route = "direct"
        logger.info("AUTO.RIA HTML via direct (retry)")
        return response
    response = await try_proxy()
    if response is not None:
        _html_route = "proxy"
        logger.info("AUTO.RIA HTML via proxy (retry)")
        return response
    return None


async def _get_html(url: str, *, params: dict | None = None) -> httpx.Response:
    """Direct першим. Проксі — лише якщо AUTO.RIA з VPS недоступний або заблокований."""
    global _html_route
    request_label = http_request_label("GET", url, params=params)

    async def try_direct() -> httpx.Response | None:
        return await _fetch_html(await _get_direct_client(), url, params)

    async def try_proxy() -> httpx.Response | None:
        if not proxy_configured():
            return None
        proxy_client = await _get_proxy_client()
        if proxy_client is None:
            return None
        return await _fetch_html(proxy_client, url, params)

    if _html_route == "direct":
        response = await try_direct()
        if response is not None:
            return response
        _html_route = None

    elif _html_route == "proxy":
        response = await try_proxy()
        if response is not None:
            return response
        await _reset_proxy_client()
        _html_route = None
        response = await try_direct()
        if response is not None:
            _html_route = "direct"
            logger.warning("AUTO.RIA HTML: proxy failed, fell back to direct")
            return response
        response = await _retry_html_fetch(try_direct=try_direct, try_proxy=try_proxy)
        if response is not None:
            return response
        _alert_html_failed()
        raise AutoRiaBetaError("AUTO.RIA HTML proxy failed", request=request_label)

    if not proxy_configured():
        response = await try_direct()
        if response is None:
            raise AutoRiaBetaError("AUTO.RIA HTML failed", request=request_label)
        _html_route = "direct"
        return response

    async def _direct_leg() -> tuple[str, httpx.Response | None]:
        return "direct", await try_direct()

    async def _proxy_leg() -> tuple[str, httpx.Response | None]:
        return "proxy", await try_proxy()

    tasks = [
        asyncio.create_task(_direct_leg()),
        asyncio.create_task(_proxy_leg()),
    ]
    pending: set[asyncio.Task] = set(tasks)
    proxy_hit: httpx.Response | None = None
    try:
        while pending:
            timeout = _PROXY_YIELD_TO_DIRECT_SECONDS if proxy_hit is not None else None
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED,
                timeout=timeout,
            )
            if timeout is not None and not done:
                break
            for task in done:
                if task.cancelled() or task.exception() is not None:
                    continue
                name, response = task.result()
                if response is None:
                    continue
                if name == "direct":
                    _html_route = "direct"
                    for leftover in pending:
                        leftover.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)
                    logger.info("AUTO.RIA HTML via direct")
                    return response
                proxy_hit = response
        if proxy_hit is not None:
            _html_route = "proxy"
            logger.info("AUTO.RIA HTML via proxy (direct unavailable)")
            return proxy_hit
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    response = await _retry_html_fetch(try_direct=try_direct, try_proxy=try_proxy)
    if response is not None:
        return response
    _alert_html_failed()
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
        cars, total = parse_search_page(response.text)
        return cars, total

    async def fetch_listing_html(self, url: str) -> str:
        response = await _get_html(url)
        await asyncio.sleep(REQUEST_DELAY_SECONDS)
        return response.text

    async def enrich_car(self, car) -> None:
        html = await self.fetch_listing_html(car.url)
        car.details = parse_listing_details(html, car)
