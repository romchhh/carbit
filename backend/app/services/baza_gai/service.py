from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import now_kyiv
from app.models.models import Listing, VinCheck
from app.schemas.schemas import VinCheckOut
from app.services.baza_gai.client import BazaGaiClient
from app.services.baza_gai.errors import BazaGaiError, BazaGaiNotFound
from app.services.baza_gai.mapper import map_vin_payload
from app.services.vin import is_valid_vin

logger = logging.getLogger(__name__)

CACHE_PREFIX = "baza-gai:vin:"
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24h KV soft-cache
# У БД тримаємо довше — щоб не спалити ліміт 1000/міс.
DB_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 днів


async def lookup_vin(
    vin: str,
    *,
    db: AsyncSession | None = None,
    listing_id: str | None = None,
) -> VinCheckOut:
    cleaned = (vin or "").strip().upper()
    if not is_valid_vin(cleaned):
        raise BazaGaiError("Некоректний VIN-код", status_code=400)

    if db is not None:
        stored = await get_stored_vin_check(db, cleaned)
        if stored is not None:
            stored.from_cache = True
            if listing_id:
                await _link_listing_vin(db, listing_id, cleaned)
            return stored

    cached = await _kv_cache_get(cleaned)
    if cached is not None:
        cached.from_cache = True
        if db is not None:
            await save_vin_check(db, cached)
            if listing_id:
                await _link_listing_vin(db, listing_id, cleaned)
        return cached

    client = BazaGaiClient()
    raw = await client.lookup_vin(cleaned)
    result = map_vin_payload(raw, vin=cleaned)
    await _kv_cache_set(cleaned, result)
    if db is not None:
        await save_vin_check(db, result)
        if listing_id:
            await _link_listing_vin(db, listing_id, cleaned)
    return result


async def get_stored_vin_check(db: AsyncSession, vin: str) -> VinCheckOut | None:
    cleaned = (vin or "").strip().upper()
    if not cleaned:
        return None
    row = await db.get(VinCheck, cleaned)
    if row is None or not isinstance(row.payload, dict):
        return None
    checked_at = row.checked_at or row.updated_at
    if checked_at is not None:
        age = (now_kyiv() - checked_at).total_seconds()
        if age > DB_MAX_AGE_SECONDS:
            return None
    try:
        out = VinCheckOut.model_validate(row.payload)
        out.from_cache = True
        return out
    except Exception:
        logger.debug("vin_check payload invalid for %s", cleaned, exc_info=True)
        return None


async def save_vin_check(db: AsyncSession, result: VinCheckOut) -> None:
    vin = result.vin.strip().upper()
    payload = result.model_dump(mode="json")
    payload["from_cache"] = False
    row = await db.get(VinCheck, vin)
    now = now_kyiv()
    if row is None:
        row = VinCheck(
            vin=vin,
            payload=payload,
            is_stolen=bool(result.is_stolen),
            digits=result.digits,
            checked_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.payload = payload
        row.is_stolen = bool(result.is_stolen)
        row.digits = result.digits
        row.updated_at = now
        # оновлюємо checked_at лише при свіжому зовнішньому запиті
        if not result.from_cache:
            row.checked_at = now
    await db.commit()


async def _link_listing_vin(db: AsyncSession, listing_id: str, vin: str) -> None:
    listing = await db.get(Listing, listing_id)
    if listing is None:
        return
    current = (listing.vin or "").strip().upper()
    if current != vin:
        listing.vin = vin
        await db.commit()


async def _kv_cache_get(vin: str) -> VinCheckOut | None:
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        raw = await redis.get(f"{CACHE_PREFIX}{vin}")
        if not raw:
            return None
        data = json.loads(raw)
        return VinCheckOut.model_validate(data)
    except Exception:
        logger.debug("baza_gai vin cache read failed", exc_info=True)
        return None


async def _kv_cache_set(vin: str, result: VinCheckOut) -> None:
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        payload = result.model_dump(mode="json")
        payload["from_cache"] = False
        await redis.setex(
            f"{CACHE_PREFIX}{vin}",
            CACHE_TTL_SECONDS,
            json.dumps(payload, ensure_ascii=False),
        )
    except Exception:
        logger.debug("baza_gai vin cache write failed", exc_info=True)


__all__ = [
    "lookup_vin",
    "get_stored_vin_check",
    "save_vin_check",
    "BazaGaiError",
    "BazaGaiNotFound",
]
