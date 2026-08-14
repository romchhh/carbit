"""Ліміт перевірок VIN: 3 унікальні на free, безліміт на платних тарифах."""

from __future__ import annotations

import json

from fastapi import HTTPException

from app.core.redis import get_redis
from app.services.billing.plans import enforce_plan_expiry, get_plan

VIN_QUOTA_PREFIX = "vin:quota:v1:"
MIN_PAID_PLAN = "lite"
# Квота «назавжди» для free-акаунта (поки не апгрейд).
QUOTA_TTL_SECONDS = 60 * 60 * 24 * 365 * 5


def effective_vin_checks_limit(user) -> int | None:
    """Скільки унікальних VIN дозволено. None = безліміт."""
    if enforce_plan_expiry(user):
        pass
    plan_id = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    if plan_id != "free":
        return None
    return max(0, int(get_plan("free").get("vin_checks_limit") or 3))


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
    """Дозволяє перевірку VIN або кидає 402.

    Повертає скільки перевірок ще лишилось (None = безліміт).
    Повторна перевірка того самого VIN не витрачає квоту.
    """
    limit = effective_vin_checks_limit(user)
    if limit is None:
        return None

    code = (vin or "").strip().upper()
    if not code:
        raise HTTPException(400, "Невалідний VIN")

    used_set = await _load_vins(user.id)
    used = len(used_set)

    if code in used_set:
        return max(0, limit - used)

    if used >= limit:
        plan = get_plan(MIN_PAID_PLAN)
        raise HTTPException(
            status_code=402,
            detail={
                "code": "vin_check_limit",
                "message": (
                    f"Безкоштовно доступно {limit} перевірки VIN. "
                    f"Оформіть тариф «{plan['name']}» — перевірки без обмежень."
                ),
                "limit": limit,
                "used": used,
                "upgrade_plan": MIN_PAID_PLAN,
            },
        )

    used_set.add(code)
    await _save_vins(user.id, used_set)
    used += 1
    return max(0, limit - used)


async def vin_quota_status(user) -> dict:
    """Статус квоти для UI."""
    limit = effective_vin_checks_limit(user)
    used = await vin_checks_usage(user.id)
    if limit is None:
        return {
            "unlimited": True,
            "limit": None,
            "used": used,
            "remaining": None,
            "upgrade_plan": MIN_PAID_PLAN,
        }
    return {
        "unlimited": False,
        "limit": limit,
        "used": min(used, limit),
        "remaining": max(0, limit - used),
        "upgrade_plan": MIN_PAID_PLAN,
    }
