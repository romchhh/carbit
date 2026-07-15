from __future__ import annotations

import asyncio
import random
from types import TracebackType

import httpx

from app.services.olx.constants import MAX_RETRIES, REQUEST_TIMEOUT, RETRYABLE_STATUS, USER_AGENTS
from app.services.olx.errors import OlxError
from app.services.olx.parser import parse_listing_details
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

    async def fetch_html(self, url: str) -> str:
        last_status: int | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
            try:
                if self._client is not None:
                    response = await self._client.get(url, headers=headers)
                else:
                    async with httpx.AsyncClient(
                        timeout=REQUEST_TIMEOUT, follow_redirects=True
                    ) as client:
                        response = await client.get(url, headers=headers)
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

    async def fetch_listing_details(self, url: str) -> dict:
        html = await self.fetch_html(url)
        return await asyncio.to_thread(parse_listing_details, html)
