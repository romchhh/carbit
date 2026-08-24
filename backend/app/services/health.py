"""Worker heartbeats and deep health helpers."""

from __future__ import annotations

import asyncio
import time

from sqlalchemy import text

from app.core.database import engine
from app.core.redis import get_redis

HEARTBEAT_TTL = 300
HEARTBEAT_PREFIX = "heartbeat:"
WORKER_HEARTBEAT_MAX_AGE = 1200.0
BOT_HEARTBEAT_MAX_AGE = 180.0
TELEGRAM_WORKER_HEARTBEAT_MAX_AGE = 60.0


def is_heartbeat_online(age: float | None, *, max_age: float) -> bool:
    return age is not None and age <= max_age


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
        return await redis.ping()
    except Exception:
        return False


async def check_database_fast(timeout: float = 1.5) -> bool:
    try:
        return await asyncio.wait_for(check_database(), timeout=timeout)
    except Exception:
        return False


async def check_kv_fast(timeout: float = 1.5) -> bool:
    try:
        return await asyncio.wait_for(check_kv(), timeout=timeout)
    except Exception:
        return False
