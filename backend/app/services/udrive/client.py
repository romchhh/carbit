from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.services.udrive.constants import UDRIVE_API_BASE_URL
from app.services.udrive.errors import UdriveError
from app.services.search.source_error import http_request_label

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (0.4, 1.0, 2.0)

_http_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Origin": "https://udrive.com.ua",
    "Referer": "https://udrive.com.ua/",
}


async def get_shared_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        return _http_client

    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=30.0,
                base_url=UDRIVE_API_BASE_URL,
                headers=_DEFAULT_HEADERS,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return _http_client


class UdriveClient:
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        last_error: Exception | None = None
        clean_path = path.lstrip("/")

        for attempt in range(_MAX_ATTEMPTS):
            request_label = http_request_label(
                method,
                f"{UDRIVE_API_BASE_URL}/{clean_path}",
                params=params,
            )
            try:
                client = await get_shared_http_client()
                response = await client.request(
                    method,
                    clean_path,
                    params=params,
                    json=json_body,
                )
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                last_error = UdriveError(
                    f"uDrive: мережева помилка: {exc}",
                    request=request_label,
                )
                if attempt + 1 >= _MAX_ATTEMPTS:
                    break
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)])
                continue

            if response.status_code >= 400:
                body = response.text[:200]
                err = UdriveError(
                    f"uDrive: помилка {response.status_code}: {body}",
                    status_code=response.status_code,
                    request=request_label,
                )
                if response.status_code in (408, 425, 429, 500, 502, 503, 504) and attempt + 1 < _MAX_ATTEMPTS:
                    await asyncio.sleep(_RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)])
                    last_error = err
                    continue
                raise err

            try:
                return response.json()
            except ValueError as exc:
                raise UdriveError("uDrive: некоректна JSON-відповідь") from exc

        raise last_error or UdriveError("uDrive: невідома помилка")

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, body: dict[str, Any]) -> Any:
        return await self._request("POST", path, json_body=body)

    async def list_makes(self) -> list[dict[str, Any]]:
        data = await self.get(
            "car-stock-service/makes",
            {"fromPageNumber": 1, "toPageNumber": 1, "pageSize": 1000},
        )
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data["items"]
        raise UdriveError("uDrive: некоректний список марок")

    async def list_models(self, make_id: int) -> list[dict[str, Any]]:
        data = await self.get(
            "car-stock-service/models",
            {
                "makeId": make_id,
                "fromPageNumber": 1,
                "toPageNumber": 1,
                "pageSize": 1000,
            },
        )
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return [m for m in data["items"] if m.get("makeId") == make_id]
        raise UdriveError("uDrive: некоректний список моделей")

    async def query_cars(self, body: dict[str, Any]) -> dict[str, Any]:
        data = await self.post("query-aggregator/cars/query", body)
        if not isinstance(data, dict):
            raise UdriveError("uDrive: очікувався об'єкт зі списком авто")
        return data

    async def get_car(self, car_id: str | int) -> dict[str, Any] | None:
        try:
            data = await self.get(f"query-aggregator/cars/{car_id}")
        except UdriveError as exc:
            if exc.status_code == 404:
                return None
            raise
        if not isinstance(data, dict):
            raise UdriveError("uDrive: очікувався об'єкт авто")
        return data
