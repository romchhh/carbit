from __future__ import annotations

from fastapi import Response

from app.core.config import settings

AUTH_COOKIE_NAME = "autoradar_token"
AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
ADMIN_COOKIE_NAME = "autoradar_admin_token"
ADMIN_COOKIE_MAX_AGE = 60 * 60 * 12


def _cookie_secure() -> bool:
    return settings.FRONTEND_URL.strip().lower().startswith("https://")


def attach_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=AUTH_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")


def attach_admin_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        max_age=ADMIN_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        path="/",
    )
