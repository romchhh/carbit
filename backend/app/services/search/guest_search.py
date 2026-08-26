"""Обмеження безкоштовного пошуку для гостей (без реєстрації)."""

from __future__ import annotations

from fastapi import Request

from app.services.rate_limit import client_ip, enforce_rate_limit

GUEST_SEARCH_LIMIT = 3
GUEST_SEARCH_WINDOW_SECONDS = 60 * 60 * 24 * 90  # 90 днів


async def enforce_guest_search_limit(request: Request) -> int:
    """Перевіряє ліміт по IP; повертає скільки безкоштовних пошуків залишилось після поточного."""
    ip = client_ip(request)
    key = f"guest-search:{ip}"
    await enforce_rate_limit(
        key=key,
        limit=GUEST_SEARCH_LIMIT,
        window_seconds=GUEST_SEARCH_WINDOW_SECONDS,
        detail="Безкоштовні пошуки вичерпано. Зареєструйтесь, щоб продовжити.",
        code="guest_search_limit",
    )

    from app.core.redis import get_redis

    redis = await get_redis()
    raw = await redis.get(f"rate:{key}")
    count = int(raw) if raw else GUEST_SEARCH_LIMIT
    return max(0, GUEST_SEARCH_LIMIT - count)
