#!/usr/bin/env python3
"""
Авторизація Telethon-клієнта та збереження сесії.

Запуск з кореня проєкту:
    PYTHONPATH=. python -m parser.auth
"""
from __future__ import annotations

import asyncio
import sys

from telethon.errors import SessionPasswordNeededError

from parser.config import settings
from parser.telegram_client import build_client


def _require_settings() -> None:
    if not settings.api_id or not settings.api_hash:
        raise RuntimeError("Задай TELETHON_API_ID і TELETHON_API_HASH у .env")
    if not settings.phone:
        raise RuntimeError("Задай TELETHON_NUMBER у .env")


async def authorize() -> None:
    _require_settings()

    print(f"📱 Телефон: ...{settings.phone[-4:]}")
    print(f"📁 Сесія: {settings.session_file}")
    print(f"📡 API ID: {settings.api_id}")
    print("📢 Канали: адмінка /admin/channels")

    client = build_client()
    await client.connect()
    print("✅ Підключено до Telegram")

    try:
        if not await client.is_user_authorized():
            print("🔐 Потрібна авторизація — надсилаю код…")
            await client.send_code_request(settings.phone)
            code = input("📲 Введи код з SMS/Telegram: ").strip()
            try:
                await client.sign_in(settings.phone, code)
            except SessionPasswordNeededError:
                password = input("🔐 Введи пароль 2FA: ").strip()
                await client.sign_in(password=password)
            print("✅ Авторизація успішна")
        else:
            print("✅ Вже авторизовано")

        me = await client.get_me()
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
    try:
        asyncio.run(authorize())
    except KeyboardInterrupt:
        print("\nСкасовано")
        sys.exit(130)
    except Exception as exc:
        print(f"❌ {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
