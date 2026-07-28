from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.services.auto_ria.constants import AUTO_RIA_BASE_URL, LANG_ID

logger = logging.getLogger(__name__)

# Скільки спроб при transient-збоях developers.ria.com (HTTPoison :closed тощо).
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (0.4, 1.0, 2.0)


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


def _is_transient_http_status(status: int, body: str) -> bool:
    """Чи варто повторити запит (тимчасовий збій upstream, не логічна помилка)."""
    if status in (408, 425, 429, 500, 502, 503, 504):
        return True
    # AUTO.RIA інколи віддає 404 з тілом Elixir HTTPoison при обриві з'єднання
    # їхнього проксі до внутрішнього сервісу — це не «ресурс не знайдено».
    if status == 404:
        low = (body or "").lower()
        if "httpoison" in low or "reason: :closed" in low or ":closed" in low:
            return True
    return False


class AutoRiaClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or settings.AUTO_RIA_API_KEY or "").strip()
        if not self.api_key:
            raise AutoRiaError("AUTO_RIA_API_KEY не налаштовано")

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        from app.services.admin.api_usage import auto_ria_operation, record_api_request

        operation = auto_ria_operation(path)
        query = {"api_key": self.api_key, "lang_id": LANG_ID}
        if params:
            query.update(params)

        last_error: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                client = await get_shared_http_client()
                response = await client.get(path, params=query)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                last_error = AutoRiaError(f"AUTO.RIA мережева помилка: {exc}")
                if attempt + 1 >= _MAX_ATTEMPTS:
                    break
                delay = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
                logger.warning(
                    "AUTO.RIA network error path=%s attempt=%s/%s: %s — retry in %.1fs",
                    path,
                    attempt + 1,
                    _MAX_ATTEMPTS,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            if response.status_code >= 400:
                body = response.text[:200]
                err = AutoRiaError(
                    f"AUTO.RIA помилка {response.status_code}: {body}",
                    status_code=response.status_code,
                )
                if (
                    _is_transient_http_status(response.status_code, body)
                    and attempt + 1 < _MAX_ATTEMPTS
                ):
                    delay = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
                    logger.warning(
                        "AUTO.RIA transient %s path=%s attempt=%s/%s — retry in %.1fs: %s",
                        response.status_code,
                        path,
                        attempt + 1,
                        _MAX_ATTEMPTS,
                        delay,
                        body[:120],
                    )
                    last_error = err
                    await asyncio.sleep(delay)
                    continue
                if _is_transient_http_status(response.status_code, body):
                    await record_api_request("auto_ria", operation, success=False)
                    raise AutoRiaError(
                        "AUTO.RIA тимчасово обірвав з'єднання. Спробуйте ще раз.",
                        status_code=response.status_code,
                    ) from err
                await record_api_request("auto_ria", operation, success=False)
                raise err

            try:
                data = response.json()
            except ValueError as exc:
                await record_api_request("auto_ria", operation, success=False)
                raise AutoRiaError("AUTO.RIA повернув некоректну відповідь") from exc

            await record_api_request("auto_ria", operation, success=True)
            return data

        assert last_error is not None
        await record_api_request("auto_ria", operation, success=False)
        raise last_error

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
