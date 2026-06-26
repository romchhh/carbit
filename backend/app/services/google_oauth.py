import secrets
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.redis import get_redis

STATE_TTL = 600
_STATE_KEY = "google_oauth_state:{state}"


def google_redirect_uri() -> str:
    if settings.GOOGLE_REDIRECT_URI:
        return settings.GOOGLE_REDIRECT_URI
    return "http://localhost:8000/api/v1/auth/google/callback"


def is_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


async def create_state() -> str:
    state = secrets.token_urlsafe(24)
    r = await get_redis()
    await r.setex(_STATE_KEY.format(state=state), STATE_TTL, "1")
    return state


async def verify_state(state: str) -> bool:
    r = await get_redis()
    key = _STATE_KEY.format(state=state)
    exists = await r.exists(key)
    if exists:
        await r.delete(key)
    return bool(exists)


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": google_redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code >= 400:
            raise RuntimeError(f"Google token error: {token_res.text}")

        access_token = token_res.json().get("access_token")
        if not access_token:
            raise RuntimeError("Google token missing access_token")

        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code >= 400:
            raise RuntimeError(f"Google userinfo error: {user_res.text}")
        return user_res.json()
