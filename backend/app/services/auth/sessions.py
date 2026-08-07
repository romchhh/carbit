"""Активні сесії користувача (пристрої) — Redis + jti в JWT."""

from __future__ import annotations

import logging
import time
import uuid

from app.core.config import settings
from app.core.redis import get_redis
from app.services.billing.plans import effective_devices_limit

logger = logging.getLogger(__name__)

SESSION_INDEX_PREFIX = "auth:sessions:"
SESSION_KEY_PREFIX = "auth:session:"


def _session_ttl_seconds() -> int:
    return max(60, int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60)


def _index_key(user_id: str) -> str:
    return f"{SESSION_INDEX_PREFIX}{user_id}"


def _session_key(user_id: str, jti: str) -> str:
    return f"{SESSION_KEY_PREFIX}{user_id}:{jti}"


async def register_session(user, jti: str) -> None:
    """Реєструє сесію; при перевищенні ліміту — відкликає найстаріші."""
    user_id = str(user.id)
    limit = max(1, int(effective_devices_limit(user)))
    ttl = _session_ttl_seconds()
    now = time.time()

    try:
        redis = await get_redis()
        index = _index_key(user_id)
        await redis.zadd(index, {jti: now})
        await redis.expire(index, ttl)
        await redis.setex(_session_key(user_id, jti), ttl, "1")

        count = await redis.zcard(index)
        if count > limit:
            excess = int(count - limit)
            old = await redis.zrange(index, 0, excess - 1)
            if old:
                await redis.zrem(index, *old)
                for old_jti in old:
                    await redis.delete(_session_key(user_id, old_jti))
                logger.info(
                    "Revoked %s old session(s) for user=%s limit=%s",
                    len(old),
                    user_id,
                    limit,
                )
    except Exception:
        logger.exception("Failed to register session for user=%s", user_id)


async def is_session_active(user_id: str, jti: str | None) -> bool:
    if not jti:
        return True
    try:
        redis = await get_redis()
        return bool(await redis.exists(_session_key(user_id, jti)))
    except Exception:
        logger.exception("Session check failed for user=%s", user_id)
        return True


async def revoke_session(user_id: str, jti: str) -> None:
    if not jti:
        return
    try:
        redis = await get_redis()
        await redis.zrem(_index_key(user_id), jti)
        await redis.delete(_session_key(user_id, jti))
    except Exception:
        logger.exception("Failed to revoke session user=%s", user_id)


async def issue_user_access_token(user) -> str:
    from app.core.security import create_access_token

    jti = str(uuid.uuid4())
    token = create_access_token(user.id, jti=jti)
    await register_session(user, jti)
    return token
