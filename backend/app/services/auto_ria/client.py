from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.config import settings
from app.services.auto_ria.constants import AUTO_RIA_BASE_URL, LANG_ID


class AutoRiaError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


_http_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def get_shared_http_client() -> httpx.AsyncClient:
    """Reuse one AsyncClient across concurrent AUTO.RIA requests."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        return _http_client

    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=20.0,
                base_url=AUTO_RIA_BASE_URL,
                limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
            )
        return _http_client


class AutoRiaClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or settings.AUTO_RIA_API_KEY or "").strip()
        if not self.api_key:
            raise AutoRiaError("AUTO_RIA_API_KEY не налаштовано")

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = {"api_key": self.api_key, "lang_id": LANG_ID}
        if params:
            query.update(params)

        client = await get_shared_http_client()
        response = await client.get(path, params=query)

        if response.status_code >= 400:
            raise AutoRiaError(
                f"AUTO.RIA помилка {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise AutoRiaError("AUTO.RIA повернув некоректну відповідь") from exc

    async def search(self, params: dict[str, Any]) -> dict[str, Any]:
        data = await self.get("/auto/search", params)
        if not isinstance(data, dict):
            raise AutoRiaError("Неочікувана відповідь пошуку AUTO.RIA")
        return data

    async def get_info(self, auto_id: int | str) -> dict[str, Any]:
        from app.services.auto_ria.details import normalize_info_response

        data = await self.get("/auto/info", {"auto_id": str(auto_id)})
        return normalize_info_response(data)

    async def get_fotos(self, auto_id: int | str) -> Any:
        return await self.get(f"/auto/fotos/{auto_id}")

    async def search_new(self, params: dict[str, Any]) -> dict[str, Any]:
        """Пошук нових авто: GET /auto/new/search (1-indexed pages, limit ≤ 50)."""
        data = await self.get("/auto/new/search", params)
        if not isinstance(data, dict):
            raise AutoRiaError("Неочікувана відповідь пошуку нових авто AUTO.RIA")
        return data

    async def get_new_info(self, auto_id: int | str) -> dict[str, Any]:
        """Деталі нового авто: GET /auto/new/auto/{AUTO_ID}."""
        data = await self.get(f"/auto/new/auto/{auto_id}")
        if not isinstance(data, dict):
            raise AutoRiaError(f"Неочікувана відповідь AUTO.RIA для нового авто {auto_id}")
        return data

    async def get_marks(self, category_id: int = 1) -> list[dict[str, Any]]:
        data = await self.get(f"/auto/categories/{category_id}/marks")
        return data if isinstance(data, list) else []

    async def get_models(self, mark_id: int, category_id: int = 1) -> list[dict[str, Any]]:
        data = await self.get(f"/auto/categories/{category_id}/marks/{mark_id}/models")
        return data if isinstance(data, list) else []
