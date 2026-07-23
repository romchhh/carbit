from __future__ import annotations

from fastapi import HTTPException

from app.core.redis import get_redis

# Live search у кабінеті: історичний каталог за фільтрами, порціями по 20
PREVIEW_MAX_PER_PAGE = 20
PREVIEW_MAX_PAGE = 25
PREVIEW_HOURLY_LIMIT = 120
PREVIEW_RATE_TTL_SECONDS = 3600

BROWSE_MAX_PER_PAGE = 12
BROWSE_MAX_PAGE = 1


def _rate_key(user_id: str) -> str:
    return f"auto_ria:preview:{user_id}"


async def consume_preview_quota(user_id: str) -> int:
    redis = await get_redis()
    key = _rate_key(user_id)
    raw = await redis.get(key)

    if raw is None:
        count = 1
        await redis.setex(key, PREVIEW_RATE_TTL_SECONDS, str(count))
    else:
        count = int(raw) + 1
        ttl = await redis.ttl(key)
        await redis.setex(key, ttl if ttl > 0 else PREVIEW_RATE_TTL_SECONDS, str(count))

    if count > PREVIEW_HOURLY_LIMIT:
        raise HTTPException(
            429,
            "Ліміт переглядів на годину вичерпано. Збережіть пошук — Carbit "
            "буде надсилати нові авто за вашими фільтрами прямо в Telegram.",
        )
    return max(PREVIEW_HOURLY_LIMIT - count, 0)


def clamp_preview_request(*, page: int, per_page: int, mode: str) -> tuple[int, int]:
    if mode == "browse":
        return min(page, BROWSE_MAX_PAGE), min(per_page, BROWSE_MAX_PER_PAGE)

    if page > PREVIEW_MAX_PAGE:
        raise HTTPException(
            400,
            f"Досягнуто ліміт перегляду ({PREVIEW_MAX_PAGE} сторінок). "
            "Збережіть пошук — Carbit надсилатиме нові авто в Telegram.",
        )
    return page, min(per_page, PREVIEW_MAX_PER_PAGE)


def is_preview_mode(mode: str) -> bool:
    return mode != "browse"
