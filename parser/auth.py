#!/usr/bin/env python3
"""
Авторизація Telethon-клієнта та збереження сесії.

Запуск з кореня проєкту:
    python auth.py
    python auth.py --reset
    PYTHONPATH=. python -m parser.auth --reset
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from telethon.errors import SessionPasswordNeededError
from telethon.errors.rpcerrorlist import AuthKeyDuplicatedError, PhoneCodeInvalidError

from parser.config import settings
from parser.session_meta import clear_session_meta, write_session_meta
from parser.telegram_client import build_client


def _require_settings() -> None:
    if not settings.api_id or not settings.api_hash:
        raise RuntimeError("Задай TELETHON_API_ID і TELETHON_API_HASH у .env")
    if not settings.phone:
        raise RuntimeError("Задай TELETHON_NUMBER у .env")


def _session_files() -> list[Path]:
    return [
        Path(settings.session_file),
        Path(f"{settings.session_path}.session"),
        Path(f"{settings.session_file}-journal"),
        Path(f"{settings.session_path}.session-journal"),
    ]


def reset_session_files() -> list[str]:
    removed: list[str] = []
    seen: set[str] = set()
    for path in _session_files():
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            path.unlink()
            removed.append(str(path))
    return removed


async def authorize(*, reset: bool = False) -> None:
    _require_settings()

    if reset:
        removed = reset_session_files()
        clear_session_meta()
        if removed:
            print("🗑️  Видалено файли сесії:")
            for p in removed:
                print(f"   {p}")
        else:
            print("ℹ️  Файлів сесії не знайдено — створимо нові")

    print(f"📱 Телефон: …{settings.phone[-4:]}")
    print(f"📁 Сесія: {settings.session_file}")
    print(f"📡 API ID: {settings.api_id}")
    print("📢 Канали: адмінка /admin/channels")

    client = build_client()
    try:
        await client.connect()
    except AuthKeyDuplicatedError as exc:
        print(
            "❌ AuthKeyDuplicated: сесію вже використовували з іншого IP/процесу.\n"
            "   Зупиніть telegram-worker (і локальний парсер), потім:\n"
            "   python auth.py --reset"
        )
        raise SystemExit(1) from exc

    print("✅ Підключено до Telegram")

    try:
        if not await client.is_user_authorized():
            print("🔐 Потрібна авторизація — надсилаю код…")
            sent = await client.send_code_request(settings.phone)
            code = input("📲 Введи код з SMS/Telegram: ").strip()
            try:
                await client.sign_in(
                    settings.phone,
                    code,
                    phone_code_hash=sent.phone_code_hash,
                )
            except SessionPasswordNeededError:
                password = input("🔐 Введи пароль 2FA: ").strip()
                await client.sign_in(password=password)
            except PhoneCodeInvalidError:
                print("❌ Невірний код")
                raise SystemExit(1)
            print("✅ Авторизація успішна")
        else:
            print("✅ Вже авторизовано")

        me = await client.get_me()
        write_session_meta(
            user_id=me.id,
            first_name=me.first_name or "",
            username=me.username,
            source="cli",
        )
        username = f"@{me.username}" if me.username else "(без username)"
        print(f"👤 {me.first_name} {username}")

        async for message in client.iter_messages("me", limit=1):
            preview = (message.text or "")[:80]
            if preview:
                print(f"📨 Тест OK — Saved Messages: {preview!r}")
            break
    finally:
        await client.disconnect()
        print(f"💾 Сесія збережена: {settings.session_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Telethon login (database/*.session)")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Видалити старі файли сесії перед входом (після AuthKeyDuplicated)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(authorize(reset=args.reset))
    except KeyboardInterrupt:
        print("\nСкасовано")
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"❌ {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
