"""Історія перевірок VIN (користувач + глобальна стрічка) через KV zset."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.core.redis import get_redis
from app.core.timezone import now_kyiv
from app.schemas.schemas import VinCheckOut

logger = logging.getLogger(__name__)

USER_HISTORY_PREFIX = "vin:history:user:v1:"
GLOBAL_HISTORY_KEY = "vin:history:global:v1"
USER_HISTORY_MAX = 40
GLOBAL_HISTORY_MAX = 60


def _user_key(user_id: str) -> str:
    return f"{USER_HISTORY_PREFIX}{user_id}"


def _entry_from_result(user_id: str, result: VinCheckOut) -> dict[str, Any]:
    title_bits = [result.vendor, result.model]
    title = " ".join(b for b in title_bits if b) or None
    if result.model_year and title:
        title = f"{result.model_year} {title}"
    elif result.model_year:
        title = str(result.model_year)
    if not title and result.auction and result.auction.title:
        title = (result.auction.title or "").split("\n")[0].strip() or None

    return {
        "vin": result.vin,
        "title": title,
        "photo_url": result.photo_url or (result.auction.photo_url if result.auction else None),
        "is_stolen": bool(result.is_stolen),
        "has_auction": bool(result.auction),
        "color": result.color,
        "checked_at": now_kyiv().isoformat(),
        "user_id": user_id,
    }


async def _trim_zset(redis, key: str, max_items: int) -> None:
    card = int(await redis.zcard(key) or 0)
    if card <= max_items:
        return
    excess = card - max_items
    old = await redis.zrange(key, 0, excess - 1)
    if old:
        await redis.zrem(key, *old)


async def record_vin_check(user_id: str, result: VinCheckOut) -> None:
    """Зберігає перевірку в історії користувача та глобальній стрічці."""
    entry = _entry_from_result(user_id, result)
    payload = json.dumps(entry, ensure_ascii=False)
    score = time.time()
    try:
        redis = await get_redis()
        user_key = _user_key(user_id)
        await redis.zadd(user_key, {payload: score})
        await _trim_zset(redis, user_key, USER_HISTORY_MAX)
        await redis.zadd(GLOBAL_HISTORY_KEY, {payload: score})
        await _trim_zset(redis, GLOBAL_HISTORY_KEY, GLOBAL_HISTORY_MAX)
    except Exception:
        logger.exception("VIN history write failed for user=%s vin=%s", user_id, result.vin)


def _parse_entries(raw_items: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_items:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        if not isinstance(raw, str):
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        vin = item.get("vin")
        if not isinstance(vin, str) or not vin:
            continue
        dedupe_key = f"{vin}:{item.get('checked_at')}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        out.append(
            {
                "vin": vin.upper(),
                "title": item.get("title") if isinstance(item.get("title"), str) else None,
                "photo_url": item.get("photo_url") if isinstance(item.get("photo_url"), str) else None,
                "is_stolen": bool(item.get("is_stolen")),
                "has_auction": bool(item.get("has_auction")),
                "color": item.get("color") if isinstance(item.get("color"), str) else None,
                "checked_at": item.get("checked_at") if isinstance(item.get("checked_at"), str) else None,
            }
        )
    return out


async def _list_history(key: str, *, limit: int, max_items: int) -> list[dict[str, Any]]:
    redis = await get_redis()
    n = max(1, min(int(limit), max_items))
    # zrange — за зростанням score; беремо хвіст і розвертаємо.
    raw = await redis.zrange(key, 0, -1)
    newest_first = list(reversed(raw or []))[:n]
    return _parse_entries(newest_first)


async def list_user_vin_history(user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    return await _list_history(_user_key(user_id), limit=limit, max_items=USER_HISTORY_MAX)


async def list_global_vin_history(*, limit: int = 20) -> list[dict[str, Any]]:
    return await _list_history(GLOBAL_HISTORY_KEY, limit=limit, max_items=GLOBAL_HISTORY_MAX)
