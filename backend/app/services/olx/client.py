from __future__ import annotations

import asyncio
import random
from types import TracebackType

import httpx

from app.services.olx.constants import (
    BASE_URL,
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


class OlxClient:
    """HTTP-клієнт OLX. У межах одного search — один AsyncClient (reuse connections)."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> OlxClient:
        self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _request_headers(self, *, accept: str) -> dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": accept,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    async def _get(self, url: str, *, headers: dict[str, str], params: dict | None = None) -> httpx.Response:
        from app.services.admin.api_usage import olx_operation, record_api_request

        operation = olx_operation(url)
        try:
            if self._client is not None:
                response = await self._client.get(url, headers=headers, params=params)
            else:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
                    response = await client.get(url, headers=headers, params=params)
            await record_api_request("olx", operation, success=response.status_code < 400)
            return response
        except Exception:
            await record_api_request("olx", operation, success=False)
            raise

    async def fetch_html(self, url: str) -> str:
        last_status: int | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            headers = self._request_headers(
                accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            )
            try:
                response = await self._get(url, headers=headers)
            except httpx.TimeoutException as exc:
                if attempt == MAX_RETRIES:
                    message = f"Таймаут при завантаженні OLX: {url}"
                    await notify_admin_parsing_error(source="OLX", error=message, url=url)
                    raise OlxError(message) from exc
                await asyncio.sleep(2 * attempt)
                continue
            except httpx.HTTPError as exc:
                if attempt == MAX_RETRIES:
                    message = f"Помилка запиту до OLX: {exc}"
                    await notify_admin_parsing_error(source="OLX", error=message, url=url)
                    raise OlxError(message) from exc
                await asyncio.sleep(2 * attempt)
                continue

            if response.status_code == 200:
                return response.text

            last_status = response.status_code
            if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                # 502/503 часто короткі; 403/429 — суворіші паузи
                delay = (5 if response.status_code in (403, 429) else 2) * attempt
                await asyncio.sleep(delay)
                continue

            # 404 часто = немає brand-path (Zeekr тощо); caller робить fallback на /q-.../
            # і сам вирішує, чи сповіщати адміна.
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
        # Без query/фільтрів API віддає всю категорію — не викликаємо «вхолосту».
        if "query" not in api_params and not params.has_remote_filters():
            return []

        url = f"{BASE_URL}{OFFERS_API_PATH}"
        last_status: int | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            headers = self._request_headers(accept="application/json")
            try:
                response = await self._get(url, headers=headers, params=api_params)
            except httpx.TimeoutException:
                if attempt == MAX_RETRIES:
                    return []
                await asyncio.sleep(2 * attempt)
                continue
            except httpx.HTTPError:
                if attempt == MAX_RETRIES:
                    return []
                await asyncio.sleep(2 * attempt)
                continue

            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError:
                    return []
                return parse_offers_api_payload(payload)

            last_status = response.status_code
            if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                delay = (5 if response.status_code in (403, 429) else 2) * attempt
                await asyncio.sleep(delay)
                continue
            return []

        _ = last_status
        return []

    async def fetch_listing_details(self, url: str) -> dict:
        html = await self.fetch_html(url)
        return await asyncio.to_thread(parse_listing_details, html)
