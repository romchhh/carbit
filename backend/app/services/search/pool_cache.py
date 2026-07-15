"""KV-кеш повного пулу live-пошуку — пагінація без повторних запитів до джерел."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.redis import get_redis
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters, SourceStatusOut
from app.services.parser.filter_groups import filters_group_key

logger = logging.getLogger(__name__)

LIVE_POOL_PREFIX = "live-pool:"
LIVE_POOL_TTL_SECONDS = 180  # 3 хвилини
# ~4 сторінки по 20 у preview — cold search без 300×hydrate
LIVE_POOL_SIZE = 80


def live_pool_cache_key(filters: SearchFilters, sort_by: str) -> str:
    payload = f"{filters_group_key(filters)}|{sort_by}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
    return f"{LIVE_POOL_PREFIX}{digest}"


async def get_live_pool(filters: SearchFilters, sort_by: str) -> dict[str, Any] | None:
    try:
        redis = await get_redis()
        raw = await redis.get(live_pool_cache_key(filters, sort_by))
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            return None
        return data
    except Exception:
        logger.exception("Live pool cache read failed")
        return None


async def set_live_pool(
    filters: SearchFilters,
    sort_by: str,
    *,
    items: list[ListingOut],
    sources: list[SourceStatusOut] | list[dict] | None = None,
    partial: bool = False,
    ttl_seconds: int = LIVE_POOL_TTL_SECONDS,
) -> None:
    try:
        redis = await get_redis()
        payload = {
            "items": [item.model_dump(mode="json") for item in items],
            "sources": [
                s.model_dump() if hasattr(s, "model_dump") else s for s in (sources or [])
            ],
            "partial": partial,
            "total": len(items),
        }
        await redis.setex(
            live_pool_cache_key(filters, sort_by),
            ttl_seconds,
            json.dumps(payload, ensure_ascii=False),
        )
    except Exception:
        logger.exception("Live pool cache write failed")


def slice_pool(
    pool: dict[str, Any],
    *,
    page: int,
    per_page: int,
) -> PaginatedListings:
    raw_items = pool.get("items") or []
    total = int(pool.get("total") or len(raw_items))
    start = (page - 1) * per_page
    end = start + per_page
    page_raw = raw_items[start:end]
    items = [ListingOut.model_validate(row) for row in page_raw]
    pages = (total + per_page - 1) // per_page if total else 0

    sources_raw = pool.get("sources") or []
    sources = [SourceStatusOut.model_validate(row) for row in sources_raw]

    return PaginatedListings(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        sources=sources,
        partial=bool(pool.get("partial")),
        from_cache=True,
    )
