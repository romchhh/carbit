import json
import secrets
from hmac import compare_digest

from app.core.redis import get_redis

CODE_TTL = 600
RESEND_COOLDOWN = 60
MAX_ATTEMPTS = 5

_KEY = "email_bind:{user_id}"
_COOLDOWN_KEY = "email_bind_cd:{user_id}"


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def resend_allowed(user_id: str) -> bool:
    r = await get_redis()
    return not await r.exists(_COOLDOWN_KEY.format(user_id=user_id))


async def store_email_bind(user_id: str, email: str) -> str:
    r = await get_redis()
    code = _generate_code()
    payload = json.dumps({"email": email, "code": code, "attempts": 0})
    await r.setex(_KEY.format(user_id=user_id), CODE_TTL, payload)
    await r.setex(_COOLDOWN_KEY.format(user_id=user_id), RESEND_COOLDOWN, "1")
    return code


async def verify_email_bind(user_id: str, email: str, code: str) -> bool:
    r = await get_redis()
    key = _KEY.format(user_id=user_id)
    raw = await r.get(key)
    if not raw:
        return False

    data = json.loads(raw)
    if data["email"].lower() != email.strip().lower():
        return False

    if not compare_digest(data["code"], code.strip()):
        data["attempts"] += 1
        if data["attempts"] >= MAX_ATTEMPTS:
            await r.delete(key)
            return False
        ttl = await r.ttl(key)
        if ttl > 0:
            await r.setex(key, ttl, json.dumps(data))
        return False

    await r.delete(key)
    return True
