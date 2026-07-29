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
    """Increment counter for key; raise 429 when over limit within window."""
    redis = await get_redis()
    full_key = f"rate:{key}"
    raw = await redis.get(full_key)
    try:
        count = int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        count = 0

    if count >= limit:
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

    count += 1
    # Не скидаємо вікно на кожному запиті — інакше ліміт «плаває» і ніколи не оновлюється.
    try:
        ttl = await redis.ttl(full_key)
        ttl_seconds = int(ttl) if isinstance(ttl, (int, float)) and int(ttl) > 0 else window_seconds
    except Exception:
        ttl_seconds = window_seconds
    await redis.setex(full_key, ttl_seconds, str(count))
