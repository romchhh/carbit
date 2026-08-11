from __future__ import annotations

import asyncio
import logging
import random
from types import TracebackType
from typing import Any

import httpx

from app.core.config import settings
from app.services.olx.constants import (
    BASE_URL,
    CATEGORY_PATH,
    MAX_RETRIES,
    OFFERS_API_LIMIT,
    OFFERS_API_PATH,
    REQUEST_TIMEOUT,
    RETRYABLE_STATUS,
    USER_AGENTS,
)
from app.services.olx.errors import OlxError
from app.services.olx.parser import (
    OlxListing,
    OlxSearchParams,
    build_offers_api_params,
    parse_listing_details,
    parse_offers_api_payload,
)
from app.services.telegram.admin_alerts import notify_admin_parsing_error

logger = logging.getLogger(__name__)

try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession

    _CURL_CFFI = True
except ImportError:  # pragma: no cover
    CurlAsyncSession = None  # type: ignore[misc, assignment]
    _CURL_CFFI = False


class OlxClient:
    """HTTP-клієнт OLX.

    CloudFront блокує httpx за TLS-відбитком → curl_cffi з impersonate Chrome.
    """

    def __init__(self) -> None:
        self._curl: Any | None = None
        self._httpx: httpx.AsyncClient | None = None
        self._warmed = False
        self._last_referer = f"{BASE_URL}/"
        self._impersonate = (settings.OLX_IMPERSONATE or "chrome131").strip() or "chrome131"
        self._proxy = (settings.OLX_PROXY_URL or "").strip() or None

    async def __aenter__(self) -> OlxClient:
        if _CURL_CFFI:
            self._curl = CurlAsyncSession()
        else:
            logger.warning("curl_cffi не встановлено — OLX може повертати 403 через CloudFront")
            self._httpx = httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True)
        await self._warm_session()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._curl is not None:
            await self._curl.close()
            self._curl = None
        if self._httpx is not None:
            await self._httpx.aclose()
            self._httpx = None
        self._warmed = False

    def _browser_headers(self, *, accept: str, referer: str | None = None) -> dict[str, str]:
        ref = referer or self._last_referer or f"{BASE_URL}/"
        headers = {
            "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": accept,
            "Referer": ref,
        }
        if not _CURL_CFFI:
            headers["User-Agent"] = random.choice(USER_AGENTS)
        return headers

    async def _warm_session(self) -> None:
        if self._warmed:
            return
        try:
            await self._get(
                f"{BASE_URL}{CATEGORY_PATH}/",
                headers=self._browser_headers(
                    accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    referer=f"{BASE_URL}/",
                ),
            )
            self._warmed = True
        except Exception:
            logger.debug("OLX session warm-up failed", exc_info=True)

    async def _get(self, url: str, *, headers: dict[str, str], params: dict | None = None) -> Any:
        from app.services.admin.api_usage import olx_operation, record_api_request

        operation = olx_operation(url)
        try:
            if self._curl is not None:
                response = await self._curl.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                    impersonate=self._impersonate,
                    proxy=self._proxy,
                )
            elif self._httpx is not None:
                response = await self._httpx.get(url, headers=headers, params=params)
            else:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
                    response = await client.get(url, headers=headers, params=params)
            await record_api_request("olx", operation, success=response.status_code < 400)
            if response.status_code < 400:
                self._last_referer = url
            return response
        except Exception:
            await record_api_request("olx", operation, success=False)
            raise

    @staticmethod
    def _retry_delay(status: int, attempt: int) -> float:
        base = 5 if status in (403, 429) else 2
        return base * attempt + random.uniform(0.2, 0.8)

    async def fetch_html(self, url: str) -> str:
        last_status: int | None = None
        referer = f"{BASE_URL}{CATEGORY_PATH}/"
        for attempt in range(1, MAX_RETRIES + 1):
            headers = self._browser_headers(
                accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                referer=referer,
            )
            try:
                response = await self._get(url, headers=headers)
            except httpx.TimeoutException as exc:
                if attempt == MAX_RETRIES:
                    message = f"Таймаут при завантаженні OLX: {url}"
                    await notify_admin_parsing_error(source="OLX", error=message, url=url)
                    raise OlxError(message) from exc
                await asyncio.sleep(self._retry_delay(504, attempt))
                continue
            except Exception as exc:
                if attempt == MAX_RETRIES:
                    message = f"Помилка запиту до OLX: {exc}"
                    await notify_admin_parsing_error(source="OLX", error=message, url=url)
                    raise OlxError(message) from exc
                await asyncio.sleep(self._retry_delay(502, attempt))
                continue

            if response.status_code == 200:
                return response.text

            last_status = response.status_code
            if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                await asyncio.sleep(self._retry_delay(response.status_code, attempt))
                continue

            message = f"OLX повернув статус {response.status_code}"
            if response.status_code != 404:
                await notify_admin_parsing_error(source="OLX", error=message, url=url)
            raise OlxError(message, status_code=response.status_code)

        message = (
            f"OLX повернув статус {last_status}"
            if last_status is not None
            else "Не вдалося завантажити сторінку OLX"
        )
        await notify_admin_parsing_error(source="OLX", error=message, url=url)
        raise OlxError(message, status_code=last_status or 502)

    async def fetch_offers_api(
        self,
        params: OlxSearchParams,
        *,
        page: int = 1,
        limit: int = OFFERS_API_LIMIT,
    ) -> list[OlxListing]:
        """Офіційний JSON API /api/v1/offers/ з серверними фільтрами."""
        api_params = build_offers_api_params(params, page=page, limit=limit)
        if "query" not in api_params and not params.has_remote_filters():
            return []

        url = f"{BASE_URL}{OFFERS_API_PATH}"
        referer = f"{BASE_URL}{CATEGORY_PATH}/"
        last_status: int | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            headers = self._browser_headers(
                accept="application/json, text/plain, */*",
                referer=referer,
            )
            try:
                response = await self._get(url, headers=headers, params=api_params)
            except Exception:
                if attempt == MAX_RETRIES:
                    return []
                await asyncio.sleep(self._retry_delay(502, attempt))
                continue

            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError:
                    return []
                return parse_offers_api_payload(payload)

            last_status = response.status_code
            if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                await asyncio.sleep(self._retry_delay(response.status_code, attempt))
                continue

            if response.status_code == 403:
                logger.warning("OLX API 403 (page=%s, params=%s)", page, api_params)
            return []

        _ = last_status
        return []

    async def fetch_offer_by_id(self, offer_id: str) -> OlxListing | None:
        """GET /api/v1/offers/{id}/ — одне оголошення для шарингу порівняння."""
        from app.services.olx.parser import _listing_from_embedded, _normalize_api_offer

        oid = str(offer_id or "").strip()
        if not oid:
            return None
        url = f"{BASE_URL}{OFFERS_API_PATH}{oid}/"
        headers = self._browser_headers(
            accept="application/json, text/plain, */*",
            referer=f"{BASE_URL}{CATEGORY_PATH}/",
        )
        try:
            response = await self._get(url, headers=headers)
        except Exception:
            return None
        if response.status_code != 200:
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if isinstance(data, dict):
            return _listing_from_embedded(_normalize_api_offer(data))
        parsed = parse_offers_api_payload(payload)
        return parsed[0] if parsed else None

    async def fetch_listing_details(self, url: str) -> dict:
        html = await self.fetch_html(url)
        return await asyncio.to_thread(parse_listing_details, html)
