"""Зберігання SMS-кодів підтвердження телефону в Redis."""

from __future__ import annotations

import json
import secrets
from hmac import compare_digest

from app.core.redis import get_redis

CODE_TTL = 600
RESEND_COOLDOWN = 60
MAX_ATTEMPTS = 5


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def _resend_allowed(cooldown_key: str) -> bool:
    r = await get_redis()
    return not await r.exists(cooldown_key)


async def _set_cooldown(cooldown_key: str) -> None:
    r = await get_redis()
    await r.setex(cooldown_key, RESEND_COOLDOWN, "1")


async def store_phone_auth(phone: str, *, intent: str, name: str | None = None) -> str:
    r = await get_redis()
    code = _generate_code()
    payload = json.dumps({"code": code, "attempts": 0, "intent": intent, "name": name})
    await r.setex(f"phone_auth:{phone}", CODE_TTL, payload)
    await _set_cooldown(f"phone_auth_cd:{phone}")
    return code


async def phone_auth_resend_allowed(phone: str) -> bool:
    return await _resend_allowed(f"phone_auth_cd:{phone}")


async def verify_phone_auth(phone: str, code: str, *, intent: str) -> dict | None:
    r = await get_redis()
    key = f"phone_auth:{phone}"
    raw = await r.get(key)
    if not raw:
        return None

    data = json.loads(raw)
    if data.get("intent") != intent:
        return None

    if not compare_digest(str(data.get("code", "")), code.strip()):
        data["attempts"] = int(data.get("attempts", 0)) + 1
        if data["attempts"] >= MAX_ATTEMPTS:
            await r.delete(key)
            return None
        ttl = await r.ttl(key)
        if ttl > 0:
            await r.setex(key, ttl, json.dumps(data))
        return None

    await r.delete(key)
    return data


async def store_phone_bind(user_id: str, phone: str) -> str:
    r = await get_redis()
    code = _generate_code()
    payload = json.dumps({"phone": phone, "code": code, "attempts": 0})
    await r.setex(f"phone_bind:{user_id}", CODE_TTL, payload)
    await _set_cooldown(f"phone_bind_cd:{user_id}")
    return code


async def phone_bind_resend_allowed(user_id: str) -> bool:
    return await _resend_allowed(f"phone_bind_cd:{user_id}")


async def verify_phone_bind(user_id: str, phone: str, code: str) -> bool:
    r = await get_redis()
    key = f"phone_bind:{user_id}"
    raw = await r.get(key)
    if not raw:
        return False

    data = json.loads(raw)
    if data.get("phone") != phone:
        return False

    if not compare_digest(str(data.get("code", "")), code.strip()):
        data["attempts"] = int(data.get("attempts", 0)) + 1
        if data["attempts"] >= MAX_ATTEMPTS:
            await r.delete(key)
            return False
        ttl = await r.ttl(key)
        if ttl > 0:
            await r.setex(key, ttl, json.dumps(data))
        return False

    await r.delete(key)
    return True
