import json
import secrets

from redis_client import get_redis

REG_TTL = 1800


async def create_registration_token(
    telegram_id: str,
    chat_id: str,
    name: str,
    email: str,
    username: str | None = None,
) -> str:
    token = secrets.token_urlsafe(24)
    r = await get_redis()
    payload = json.dumps({
        "telegram_id": telegram_id,
        "chat_id": chat_id,
        "name": name,
        "email": email,
        "username": username,
    })
    await r.setex(f"tg:register:{token}", REG_TTL, payload)
    return token
