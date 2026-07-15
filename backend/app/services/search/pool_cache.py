"""KV-кеш live-пулу: ліниві батчі AUTO.RIA / OLX / Telegram по 10 карток."""

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
LIVE_POOL_TTL_SECONDS = 300  # 5 хв — лінива гідрація розтягує сесію «Показати ще»
# Скільки AUTO.RIA id збираємо на cold search (дешево); get_info — лише по видимих батчах
LIVE_POOL_SIZE = 120
# Скільки карток підвантажуємо за раз (як у FE SEARCH_PAGE_SIZE)
HYDRATE_BATCH_SIZE = 10


def live_pool_cache_key(filters: SearchFilters, sort_by: str) -> str:
    payload = f"{filters_group_key(filters)}|{sort_by}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
    return f"{LIVE_POOL_PREFIX}{digest}"


def pool_display_total(pool: dict[str, Any]) -> int:
    items_n = len(pool.get("items") or [])
    pending_ria = len(pool.get("pending_ria_ids") or [])
    market = int(pool.get("market_total") or 0)
    soft = items_n + pending_ria
    # Джерела ще не вичерпані → можна показати «Показати ще»
    if not pool.get("olx_exhausted", True):
        soft += HYDRATE_BATCH_SIZE
    if not pool.get("tg_exhausted", True):
        soft += HYDRATE_BATCH_SIZE
    return max(market, soft, items_n)


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
    pool: dict[str, Any],
    ttl_seconds: int = LIVE_POOL_TTL_SECONDS,
) -> None:
    """Зберігає повний стан пулу (items + pending + курсори джерел)."""
    try:
        redis = await get_redis()
        items = pool.get("items") or []
        # Нормалізуємо ListingOut → dict
        normalized_items = []
        for row in items:
            if isinstance(row, ListingOut):
                normalized_items.append(row.model_dump(mode="json"))
            elif isinstance(row, dict):
                normalized_items.append(row)
        pending = [str(x) for x in (pool.get("pending_ria_ids") or []) if str(x).strip()]
        sources_raw = pool.get("sources") or []
        sources = []
        for s in sources_raw:
            if hasattr(s, "model_dump"):
                sources.append(s.model_dump())
            elif isinstance(s, dict):
                sources.append(s)

        payload = {
            "items": normalized_items,
            "pending_ria_ids": pending,
            "ria_fetched": int(pool.get("ria_fetched") or 0),
            "olx_next_page": int(pool.get("olx_next_page") or 1),
            "olx_fetched": int(pool.get("olx_fetched") or 0),
            "olx_exhausted": bool(pool.get("olx_exhausted", False)),
            "olx_total": int(pool.get("olx_total") or 0),
            "tg_next_page": int(pool.get("tg_next_page") or 1),
            "tg_fetched": int(pool.get("tg_fetched") or 0),
            "tg_exhausted": bool(pool.get("tg_exhausted", False)),
            "tg_total": int(pool.get("tg_total") or 0),
            "tg_enabled": bool(pool.get("tg_enabled", False)),
            "sources": sources,
            "partial": bool(pool.get("partial")),
            "market_total": int(pool.get("market_total") or 0),
        }
        payload["total"] = pool_display_total(payload)
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
    total = pool_display_total(pool)
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
