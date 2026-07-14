from __future__ import annotations

from fastapi import Response

from app.core.config import settings

AUTH_COOKIE_NAME = "autoradar_token"
AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
ADMIN_COOKIE_NAME = "autoradar_admin_token"
ADMIN_COOKIE_MAX_AGE = 60 * 60 * 12


def _cookie_secure() -> bool:
    return settings.FRONTEND_URL.strip().lower().startswith("https://")


def _cookie_base(*, httponly: bool = True) -> dict:
    return {
        "path": "/",
        "httponly": httponly,
        "samesite": "lax",
        "secure": _cookie_secure(),
    }


def attach_auth_cookie(
    response: Response,
    token: str,
    *,
    max_age: int | None = AUTH_COOKIE_MAX_AGE,
) -> None:
    """Set user session cookie. max_age=None → session cookie (до закриття браузера)."""
    kwargs = {
        "key": AUTH_COOKIE_NAME,
        "value": token,
        **_cookie_base(),
    }
    if max_age is not None:
        kwargs["max_age"] = max_age
    response.set_cookie(**kwargs)


def clear_auth_cookie(response: Response) -> None:
    base = _cookie_base()
    response.delete_cookie(key=AUTH_COOKIE_NAME, **base)
    # Дубль: деякі проксі/браузери надійніше знімають через явне max_age=0
    response.set_cookie(key=AUTH_COOKIE_NAME, value="", max_age=0, expires=0, **base)


def attach_admin_cookie(
    response: Response,
    token: str,
    *,
    max_age: int | None = ADMIN_COOKIE_MAX_AGE,
) -> None:
    kwargs = {
        "key": ADMIN_COOKIE_NAME,
        "value": token,
        **_cookie_base(),
    }
    if max_age is not None:
        kwargs["max_age"] = max_age
    response.set_cookie(**kwargs)


def clear_admin_cookie(response: Response) -> None:
    base = _cookie_base()
    response.delete_cookie(key=ADMIN_COOKIE_NAME, **base)
    response.set_cookie(key=ADMIN_COOKIE_NAME, value="", max_age=0, expires=0, **base)
