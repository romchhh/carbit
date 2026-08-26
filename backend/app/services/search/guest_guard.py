"""Захист гостьового пошуку від прямого парсингу API."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request

from app.core.config import settings
from app.services.admin.visit_stats import is_bot_user_agent
from app.services.rate_limit import client_ip, enforce_rate_limit

GUEST_BURST_LIMIT = 8
GUEST_BURST_WINDOW_SECONDS = 60


def verify_guest_internal_secret(
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
) -> None:
    """Дозволяє виклик лише з Next.js proxy (спільний INTERNAL_API_SECRET)."""
    expected = settings.INTERNAL_API_SECRET or ""
    provided = x_internal_secret or ""
    if not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(403, "Forbidden")


async def enforce_guest_search_protection(request: Request) -> None:
    """Блокує ботів і надто часті запити з одного IP."""
    if is_bot_user_agent(request.headers.get("user-agent")):
        raise HTTPException(403, "Forbidden")

    ip = client_ip(request)
    await enforce_rate_limit(
        key=f"guest-search-burst:{ip}",
        limit=GUEST_BURST_LIMIT,
        window_seconds=GUEST_BURST_WINDOW_SECONDS,
        detail="Занадто багато запитів. Спробуйте пізніше.",
        code="guest_search_burst",
    )
