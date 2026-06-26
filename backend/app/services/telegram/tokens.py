import json
import secrets

from app.core.redis import get_redis

CONNECT_TTL = 900
REG_TTL = 1800
LOGIN_TTL = 900


async def create_connect_token(user_id: str) -> str:
    token = secrets.token_urlsafe(16)
    r = await get_redis()
    await r.setex(f"tg:connect:{token}", CONNECT_TTL, user_id)
    return token


async def consume_connect_token(token: str) -> str | None:
    r = await get_redis()
    key = f"tg:connect:{token}"
    user_id = await r.get(key)
    if user_id:
        await r.delete(key)
    return user_id


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


async def get_registration_token(token: str) -> dict | None:
    r = await get_redis()
    raw = await r.get(f"tg:register:{token}")
    if not raw:
        return None
    return json.loads(raw)


async def delete_registration_token(token: str) -> None:
    r = await get_redis()
    await r.delete(f"tg:register:{token}")


async def create_login_token(user_id: str) -> str:
    token = secrets.token_urlsafe(24)
    r = await get_redis()
    await r.setex(f"tg:login:{token}", LOGIN_TTL, user_id)
    return token


async def consume_login_token(token: str) -> str | None:
    r = await get_redis()
    key = f"tg:login:{token}"
    user_id = await r.get(key)
    if user_id:
        await r.delete(key)
    return user_id
