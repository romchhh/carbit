"""Worker heartbeats and deep health helpers."""

from __future__ import annotations

import time

from app.core.redis import get_redis
from sqlalchemy import text

from app.core.database import engine

HEARTBEAT_TTL = 300
HEARTBEAT_PREFIX = "heartbeat:"


async def beat(service: str) -> None:
    redis = await get_redis()
    await redis.setex(f"{HEARTBEAT_PREFIX}{service}", HEARTBEAT_TTL, str(time.time()))


async def heartbeat_age_seconds(service: str) -> float | None:
    redis = await get_redis()
    raw = await redis.get(f"{HEARTBEAT_PREFIX}{service}")
    if not raw:
        return None
    try:
        return max(0.0, time.time() - float(raw))
    except (TypeError, ValueError):
        return None


async def check_database() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_kv() -> bool:
    try:
        redis = await get_redis()
        await redis.setex("health:ping", 30, "1")
        return (await redis.get("health:ping")) == "1"
    except Exception:
        return False
