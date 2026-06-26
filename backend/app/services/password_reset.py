import json
import secrets

from app.core.redis import get_redis

RESET_TTL = 3600
COOLDOWN_TTL = 60

_TOKEN_KEY = "pwd_reset:{token}"
_COOLDOWN_KEY = "pwd_reset_cooldown:{email}"


async def create_reset_token(user_id: str, email: str) -> str:
    token = secrets.token_urlsafe(32)
    r = await get_redis()
    payload = json.dumps({"user_id": user_id, "email": email})
    await r.setex(_TOKEN_KEY.format(token=token), RESET_TTL, payload)
    return token


async def resend_allowed(email: str) -> bool:
    r = await get_redis()
    return not await r.exists(_COOLDOWN_KEY.format(email=email))


async def set_cooldown(email: str) -> None:
    r = await get_redis()
    await r.setex(_COOLDOWN_KEY.format(email=email), COOLDOWN_TTL, "1")


async def consume_reset_token(token: str) -> dict | None:
    r = await get_redis()
    key = _TOKEN_KEY.format(token=token)
    raw = await r.get(key)
    if not raw:
        return None
    await r.delete(key)
    return json.loads(raw)
