from __future__ import annotations

import asyncio
import random

import httpx

from app.services.olx.constants import MAX_RETRIES, REQUEST_TIMEOUT, USER_AGENTS
from app.services.olx.errors import OlxError
from app.services.olx.parser import parse_listing_details
from app.services.telegram.admin_alerts import notify_admin_parsing_error


class OlxClient:
    async def fetch_html(self, url: str) -> str:
        for attempt in range(1, MAX_RETRIES + 1):
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
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

            if response.status_code in (403, 429):
                await asyncio.sleep(5 * attempt)
                continue

            message = f"OLX повернув статус {response.status_code}"
            await notify_admin_parsing_error(source="OLX", error=message, url=url)
            raise OlxError(message, status_code=response.status_code)

        message = "Не вдалося завантажити сторінку OLX"
        await notify_admin_parsing_error(source="OLX", error=message, url=url)
        raise OlxError(message)

    async def fetch_listing_details(self, url: str) -> dict:
        html = await self.fetch_html(url)
        return await asyncio.to_thread(parse_listing_details, html)
