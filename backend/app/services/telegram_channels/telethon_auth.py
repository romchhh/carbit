"""Telethon user-session: статус, скидання, авторизація через адмінку (кроки код / 2FA)."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.core.config import settings as app_settings
from app.core.redis import get_redis
from app.services.telegram_channels.bootstrap import ensure_parser_path

logger = logging.getLogger(__name__)

PENDING_AUTH_KEY = "telethon:auth:pending"
PENDING_AUTH_TTL = 600


def _mask_phone(phone: str) -> str:
    digits = (phone or "").strip()
    if len(digits) < 4:
        return "—"
    return f"…{digits[-4:]}"


def _parser_settings():
    ensure_parser_path()
    from parser.config import settings as parser_settings

    return parser_settings


def _session_paths() -> list[Path]:
    ps = _parser_settings()
    paths = [
        Path(ps.session_file),
        Path(f"{ps.session_path}.session"),
        Path(f"{ps.session_file}-journal"),
        Path(f"{ps.session_path}.session-journal"),
    ]
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve()) if p.is_absolute() or p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


async def _load_pending() -> dict[str, Any] | None:
    redis = await get_redis()
    raw = await redis.get(PENDING_AUTH_KEY)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


async def _save_pending(data: dict[str, Any]) -> None:
    redis = await get_redis()
    payload = {**data, "updated_at": time.time()}
    await redis.setex(PENDING_AUTH_KEY, PENDING_AUTH_TTL, json.dumps(payload, ensure_ascii=False))


async def _clear_pending() -> None:
    redis = await get_redis()
    await redis.delete(PENDING_AUTH_KEY)


async def get_telethon_session_status() -> dict[str, Any]:
    ps = _parser_settings()
    session_file = Path(ps.session_file)
    out: dict[str, Any] = {
        "telethon_configured": bool(app_settings.TELETHON_API_ID and app_settings.TELETHON_API_HASH),
        "phone_configured": bool(ps.phone or app_settings.TELETHON_NUMBER),
        "phone_masked": _mask_phone(ps.phone or app_settings.TELETHON_NUMBER),
        "session_file": ps.session_file,
        "session_exists": session_file.exists(),
        "authorized": False,
        "user": None,
        "error": None,
        "error_code": None,
        "auth_step": None,
    }

    pending = await _load_pending()
    if pending:
        if pending.get("needs_password"):
            out["auth_step"] = "password"
        else:
            out["auth_step"] = "code"

    if not out["telethon_configured"]:
        out["error"] = "Задайте TELETHON_API_ID і TELETHON_API_HASH у .env"
        out["error_code"] = "not_configured"
        return out

    if not out["phone_configured"]:
        out["error"] = "Задайте TELETHON_NUMBER у .env"
        out["error_code"] = "no_phone"
        return out

    from parser.telegram_client import build_client
    from telethon.errors.rpcerrorlist import AuthKeyDuplicatedError

    client = build_client()
    try:
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            out["authorized"] = True
            out["user"] = {
                "id": me.id,
                "first_name": me.first_name or "",
                "username": me.username,
            }
    except AuthKeyDuplicatedError:
        out["error"] = (
            "Сесію зіпсовано (AuthKeyDuplicated): один .session одночасно з двох IP/процесів. "
            "Зупиніть telegram-worker, скиньте сесію і увійдіть знову."
        )
        out["error_code"] = "auth_key_duplicated"
    except Exception as exc:
        logger.exception("Telethon session check failed")
        out["error"] = str(exc)[:300]
        out["error_code"] = "connect_failed"
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    return out


async def reset_telethon_session() -> dict[str, Any]:
    removed: list[str] = []
    for path in _session_paths():
        if path.exists():
            path.unlink()
            removed.append(str(path))
    await _clear_pending()
    return {"removed": removed, "session_file": _parser_settings().session_file}


async def send_telethon_login_code() -> dict[str, Any]:
    ps = _parser_settings()
    phone = (ps.phone or app_settings.TELETHON_NUMBER or "").strip()
    if not phone:
        raise HTTPException(400, "TELETHON_NUMBER не задано у .env")

    from parser.telegram_client import build_client
    from telethon.errors.rpcerrorlist import AuthKeyDuplicatedError

    client = build_client()
    try:
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            await _clear_pending()
            return {
                "status": "already_authorized",
                "phone_masked": _mask_phone(phone),
                "user": {
                    "id": me.id,
                    "first_name": me.first_name or "",
                    "username": me.username,
                },
            }

        sent = await client.send_code_request(phone)
        await _save_pending(
            {
                "phone": phone,
                "phone_code_hash": sent.phone_code_hash,
                "needs_password": False,
            }
        )
        return {
            "status": "code_sent",
            "phone_masked": _mask_phone(phone),
        }
    except AuthKeyDuplicatedError as exc:
        raise HTTPException(
            409,
            "Сесія недійсна (AuthKeyDuplicated). Спочатку «Скинути сесію», потім надішліть код знову.",
        ) from exc
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


async def confirm_telethon_code(code: str) -> dict[str, Any]:
    code = (code or "").strip().replace(" ", "")
    if not code or not code.isdigit():
        raise HTTPException(400, "Введіть код з SMS/Telegram (лише цифри)")

    pending = await _load_pending()
    if not pending or not pending.get("phone_code_hash"):
        raise HTTPException(400, "Спочатку натисніть «Надіслати код»")

    from parser.telegram_client import build_client
    from telethon.errors import SessionPasswordNeededError
    from telethon.errors.rpcerrorlist import AuthKeyDuplicatedError, PhoneCodeInvalidError

    client = build_client()
    try:
        await client.connect()
        try:
            await client.sign_in(
                pending["phone"],
                code,
                phone_code_hash=pending["phone_code_hash"],
            )
        except SessionPasswordNeededError:
            await _save_pending({**pending, "needs_password": True})
            return {"status": "password_required", "phone_masked": _mask_phone(pending["phone"])}
        except PhoneCodeInvalidError as exc:
            raise HTTPException(400, "Невірний код. Спробуйте ще раз або надішліть новий код.") from exc

        me = await client.get_me()
        await _clear_pending()
        return {
            "status": "ok",
            "phone_masked": _mask_phone(pending["phone"]),
            "user": {
                "id": me.id,
                "first_name": me.first_name or "",
                "username": me.username,
            },
        }
    except AuthKeyDuplicatedError as exc:
        raise HTTPException(409, "Сесія недійсна. Скиньте сесію і повторіть вхід.") from exc
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


async def confirm_telethon_password(password: str) -> dict[str, Any]:
    password = (password or "").strip()
    if not password:
        raise HTTPException(400, "Введіть пароль двофакторної автентифікації")

    pending = await _load_pending()
    if not pending or not pending.get("needs_password"):
        raise HTTPException(400, "Спочатку підтвердьте код з SMS/Telegram")

    from parser.telegram_client import build_client
    from telethon.errors import PasswordHashInvalidError
    from telethon.errors.rpcerrorlist import AuthKeyDuplicatedError

    client = build_client()
    try:
        await client.connect()
        try:
            await client.sign_in(password=password)
        except PasswordHashInvalidError as exc:
            raise HTTPException(400, "Невірний пароль 2FA") from exc

        me = await client.get_me()
        await _clear_pending()
        return {
            "status": "ok",
            "phone_masked": _mask_phone(pending.get("phone", "")),
            "user": {
                "id": me.id,
                "first_name": me.first_name or "",
                "username": me.username,
            },
        }
    except AuthKeyDuplicatedError as exc:
        raise HTTPException(409, "Сесія недійсна. Скиньте сесію і повторіть вхід.") from exc
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
