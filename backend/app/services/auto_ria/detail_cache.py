"""Кеш /auto/info по auto_id — менше спалимо ліміт AUTO.RIA при повторних пошуках.

Шари:
1) KV (Redis/SQLite) — повний info JSON, TTL 14 днів (чистка автоматична)
2) Таблиця listings — якщо вже інгестили авто з фото, беремо картку з БД без API
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Any

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.timezone import as_kyiv, now_kyiv
from app.models.models import Listing, Source
from app.schemas.schemas import ListingOut
from app.services.listings.serialize import listing_to_out

logger = logging.getLogger(__name__)

CACHE_PREFIX = "auto_ria:info:"
# 14 днів — як просили; KV expires_at = авто-чистка без окремого cron
CACHE_TTL_SECONDS = 60 * 60 * 24 * 14
DB_MAX_AGE = timedelta(days=14)


def listing_id_for(auto_id: str) -> str:
    return f"auto_ria_{auto_id}"


async def get_info(auto_id: str) -> dict[str, Any] | None:
    aid = str(auto_id).strip()
    if not aid:
        return None
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        raw = await redis.get(f"{CACHE_PREFIX}{aid}")
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        # Підтримка старого формату {..info fields..} і обгортки {"info": {...}}
        info = data.get("info") if isinstance(data.get("info"), dict) else data
        if not isinstance(info, dict) or not info:
            return None
        return info
    except Exception:
        logger.debug("auto_ria info cache read failed id=%s", aid, exc_info=True)
        return None


async def set_info(auto_id: str, info: dict[str, Any]) -> None:
    aid = str(auto_id).strip()
    if not aid or not isinstance(info, dict):
        return
    try:
        from app.core.redis import get_redis
        from app.services.auto_ria.details import extract_image_urls

        redis = await get_redis()
        images = extract_image_urls(info, None)
        payload = {"info": info, "images": images, "cached_at": now_kyiv().isoformat()}
        await redis.setex(
            f"{CACHE_PREFIX}{aid}",
            CACHE_TTL_SECONDS,
            json.dumps(payload, ensure_ascii=False, default=str),
        )
    except Exception:
        logger.debug("auto_ria info cache write failed id=%s", aid, exc_info=True)


async def get_many_infos(auto_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Parallel KV gets — KV клієнт без mget."""
    out: dict[str, dict[str, Any]] = {}
    if not auto_ids:
        return out

    import asyncio

    async def one(aid: str) -> None:
        info = await get_info(aid)
        if info is not None:
            out[aid] = info

    await asyncio.gather(*(one(str(a).strip()) for a in auto_ids if str(a).strip()))
    return out


async def get_fresh_listings_from_db(auto_ids: list[str]) -> dict[str, ListingOut]:
    """Уже збережені AUTO.RIA-картки з фото — без повторного get_info."""
    aids = [str(a).strip() for a in auto_ids if str(a).strip()]
    if not aids:
        return {}

    listing_ids = [listing_id_for(a) for a in aids]
    cutoff = now_kyiv() - DB_MAX_AGE
    result: dict[str, ListingOut] = {}

    try:
        async with AsyncSessionLocal() as db:
            rows = (
                await db.scalars(
                    select(Listing).where(
                        Listing.id.in_(listing_ids),
                        Listing.source == Source.auto_ria,
                    )
                )
            ).all()
            for row in rows:
                freshest = row.refreshed_at or row.found_at
                if freshest is None:
                    continue
                try:
                    if as_kyiv(freshest) < cutoff:
                        continue
                except Exception:
                    continue
                # Без фото немає сенсу вважати це «готовим» — тягнемо API заради photoData
                if not (row.images or []):
                    continue
                aid = (row.external_id or "").strip() or row.id.removeprefix("auto_ria_")
                if not aid:
                    continue
                result[aid] = listing_to_out(row)
    except Exception:
        logger.debug("auto_ria listing DB cache read failed", exc_info=True)

    return result


async def resolve_listings(
    auto_ids: list[str],
    *,
    fetch_info,
) -> list[ListingOut]:
    """Гідрація ID: KV → БД (з фото) → API fetch_info(auto_id)."""
    from app.services.auto_ria.mapper import info_to_listing

    aids = [str(a).strip() for a in auto_ids if str(a).strip()]
    if not aids:
        return []

    resolved: dict[str, ListingOut] = {}

    kv_hits = await get_many_infos(aids)
    for aid, info in kv_hits.items():
        try:
            listing = info_to_listing(info, fotos=None)
            listing.refreshed_at = listing.refreshed_at or now_kyiv()
            resolved[aid] = listing
        except Exception:
            logger.debug("bad cached info for %s", aid, exc_info=True)

    missing = [a for a in aids if a not in resolved]
    if missing:
        db_hits = await get_fresh_listings_from_db(missing)
        resolved.update(db_hits)

    still_missing = [a for a in aids if a not in resolved]
    if still_missing:
        import asyncio

        async def fetch_one(aid: str) -> None:
            try:
                info = await fetch_info(aid)
                if not isinstance(info, dict):
                    return
                await set_info(aid, info)
                listing = info_to_listing(info, fotos=None)
                listing.refreshed_at = now_kyiv()
                resolved[aid] = listing
            except Exception:
                logger.debug("auto_ria hydrate miss id=%s", aid, exc_info=True)

        # Зберігаємо семафор викликача — тут просто gather; caller обгортає fetch_info
        await asyncio.gather(*(fetch_one(a) for a in still_missing))

    # Порядок як у search ids
    return [resolved[a] for a in aids if a in resolved]


__all__ = [
    "CACHE_TTL_SECONDS",
    "get_info",
    "set_info",
    "get_many_infos",
    "get_fresh_listings_from_db",
    "resolve_listings",
    "listing_id_for",
]
