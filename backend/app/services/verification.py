import json
import secrets
from hmac import compare_digest

from app.core.redis import get_redis

CODE_TTL = 600
RESEND_COOLDOWN = 60
MAX_ATTEMPTS = 5

_KEY = "reg:{email}"
_COOLDOWN_KEY = "reg_cooldown:{email}"


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def store_registration(email: str, name: str, hashed_password: str) -> str:
    r = await get_redis()
    code = _generate_code()
    payload = json.dumps({
        "code": code,
        "name": name,
        "hashed_password": hashed_password,
        "attempts": 0,
    })
    await r.setex(_KEY.format(email=email), CODE_TTL, payload)
    await r.setex(_COOLDOWN_KEY.format(email=email), RESEND_COOLDOWN, "1")
    return code


async def resend_allowed(email: str) -> bool:
    r = await get_redis()
    return not await r.exists(_COOLDOWN_KEY.format(email=email))


async def set_resend_cooldown(email: str) -> None:
    r = await get_redis()
    await r.setex(_COOLDOWN_KEY.format(email=email), RESEND_COOLDOWN, "1")


async def get_registration(email: str) -> dict | None:
    r = await get_redis()
    raw = await r.get(_KEY.format(email=email))
    if not raw:
        return None
    return json.loads(raw)


async def verify_code(email: str, code: str) -> dict | None:
    r = await get_redis()
    key = _KEY.format(email=email)
    raw = await r.get(key)
    if not raw:
        return None

    data = json.loads(raw)
    if not compare_digest(data["code"], code.strip()):
        data["attempts"] += 1
        if data["attempts"] >= MAX_ATTEMPTS:
            await r.delete(key)
            return None
        ttl = await r.ttl(key)
        if ttl > 0:
            await r.setex(key, ttl, json.dumps(data))
        return None

    await r.delete(key)
    return data


async def refresh_code(email: str) -> str | None:
    r = await get_redis()
    key = _KEY.format(email=email)
    raw = await r.get(key)
    if not raw:
        return None

    data = json.loads(raw)
    code = _generate_code()
    data["code"] = code
    data["attempts"] = 0
    ttl = await r.ttl(key)
    if ttl <= 0:
        ttl = CODE_TTL
    await r.setex(key, ttl, json.dumps(data))
    await r.setex(_COOLDOWN_KEY.format(email=email), RESEND_COOLDOWN, "1")
    return code
