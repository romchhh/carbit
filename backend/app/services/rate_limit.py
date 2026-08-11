"""Simple KV-backed rate limiter for auth and search endpoints."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.core.redis import get_redis


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def enforce_rate_limit(
    *,
    key: str,
    limit: int,
    window_seconds: int,
    detail: str = "Занадто багато спроб. Спробуйте пізніше.",
    code: str | None = None,
) -> None:
    """Increment counter for key; raise 429 when over limit within window.

    Атомна реалізація: INCR повертає новий лічильник і гарантує відсутність
    race condition між get+set (кілька конкурентних запитів не можуть обходити ліміт).
    EXPIRE встановлюється лише при першому INCR (count == 1), щоб вікно не «плавало».
    """
    redis = await get_redis()
    full_key = f"rate:{key}"

    count = await redis.incr(full_key)
    if count == 1:
        # Перший запит у вікні — встановлюємо TTL
        await redis.expire(full_key, window_seconds)

    if count > limit:
        retry_after = window_seconds
        try:
            ttl = await redis.ttl(full_key)
            if isinstance(ttl, (int, float)) and int(ttl) > 0:
                retry_after = int(ttl)
        except Exception:
            pass
        payload: dict | str
        if code:
            payload = {
                "code": code,
                "message": detail,
                "retry_after": retry_after,
            }
        else:
            payload = detail
        raise HTTPException(
            status_code=429,
            detail=payload,
            headers={"Retry-After": str(retry_after)},
        )
