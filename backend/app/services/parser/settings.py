from __future__ import annotations

import json

from app.core.timezone import now_kyiv

from app.core.redis import get_redis

SETTINGS_KEY = "parser:settings"
CACHE_PREFIX = "parser:cache:"
DEFAULT_SETTINGS = {
    "enabled": True,
    "interval_seconds": 900,
    "max_listings_per_group": 30,
    "cache_ttl_seconds": 1800,
    "notify_telegram": True,
    "telegram_enabled": True,
    "telegram_history_limit": 100,
}


async def get_parser_settings() -> dict:
    redis = await get_redis()
    raw = await redis.get(SETTINGS_KEY)
    if not raw:
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return dict(DEFAULT_SETTINGS)
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    return merged


async def save_parser_settings(settings: dict) -> dict:
    redis = await get_redis()
    current = await get_parser_settings()
    current.update({k: v for k, v in settings.items() if k in DEFAULT_SETTINGS})
    await redis.setex(SETTINGS_KEY, 86400 * 365, json.dumps(current, ensure_ascii=False))
    return current


async def get_filter_cache(filter_key: str) -> dict | None:
    redis = await get_redis()
    raw = await redis.get(f"{CACHE_PREFIX}{filter_key}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def set_filter_cache(filter_key: str, listing_ids: list[str], *, ttl_seconds: int) -> None:
    redis = await get_redis()
    payload = json.dumps(
        {"listing_ids": listing_ids, "fetched_at": now_kyiv().isoformat()},
        ensure_ascii=False,
    )
    await redis.setex(f"{CACHE_PREFIX}{filter_key}", ttl_seconds, payload)
