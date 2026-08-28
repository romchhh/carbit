"""Перевірки VIN — безліміт на всіх тарифах."""

from __future__ import annotations

import json

from fastapi import HTTPException

from app.core.redis import get_redis

VIN_QUOTA_PREFIX = "vin:quota:v1:"
QUOTA_TTL_SECONDS = 60 * 60 * 24 * 365 * 5


def effective_vin_checks_limit(user) -> int | None:
    """Скільки унікальних VIN дозволено. None = безліміт (усі тарифи)."""
    return None


def _quota_key(user_id: str) -> str:
    return f"{VIN_QUOTA_PREFIX}{user_id}"


async def _load_vins(user_id: str) -> set[str]:
    redis = await get_redis()
    raw = await redis.get(_quota_key(user_id))
    if not raw:
        return set()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, list):
        return set()
    return {str(v).upper() for v in data if isinstance(v, str) and v}


async def _save_vins(user_id: str, vins: set[str]) -> None:
    redis = await get_redis()
    await redis.setex(
        _quota_key(user_id),
        QUOTA_TTL_SECONDS,
        json.dumps(sorted(vins), ensure_ascii=False),
    )


async def vin_checks_usage(user_id: str) -> int:
    return len(await _load_vins(user_id))


async def enforce_vin_check_quota(user, vin: str) -> int | None:
    """Дозволяє перевірку VIN. Повертає None (безліміт)."""
    code = (vin or "").strip().upper()
    if not code:
        raise HTTPException(400, "Невалідний VIN")

    used_set = await _load_vins(user.id)
    if code not in used_set:
        used_set.add(code)
        await _save_vins(user.id, used_set)
    return None


async def vin_quota_status(user) -> dict:
    """Статус квоти для UI."""
    used = await vin_checks_usage(user.id)
    return {
        "unlimited": True,
        "limit": None,
        "used": used,
        "remaining": None,
        "upgrade_plan": None,
    }
