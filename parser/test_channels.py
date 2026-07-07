#!/usr/bin/env python3
"""
Тест парсингу Telegram-каналів (без запису в БД).

    PYTHONPATH=. python -m parser.test_channels
    PYTHONPATH=. python -m parser.test_channels --limit 5 --channel @ua_autobazar
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from parser.config import settings
from parser.service import CarParserService


async def run(*, limit: int, channels: list[str], fresh: bool) -> int:
    if not settings.api_id or not settings.api_hash:
        print("❌ TELETHON_API_ID / TELETHON_API_HASH не задані")
        return 1
    if not settings.phone:
        print("❌ TELETHON_NUMBER не заданий")
        return 1

    service = CarParserService(fresh_dedupe=fresh)
    await service.start()
    if fresh:
        print("🔄 Dedupe очищено (--fresh)")

    total = 0
    try:
        for channel in channels:
            print(f"\n=== {channel} ===")
            try:
                listings = await service.parse_channel_history(channel, limit=limit)
            except Exception as exc:
                print(f"❌ Помилка: {exc}")
                continue

            print(f"✓ Знайдено {len(listings)} оголошень")
            total += len(listings)
            for item in listings[:3]:
                sample = {
                    "channel": item.channel,
                    "brand": item.brand,
                    "model": item.model,
                    "year": item.year,
                    "price": item.price_amount,
                    "currency": item.price_currency,
                    "link": item.source_link,
                    "confidence": round(item.confidence, 2),
                    "text": (item.raw_text or "")[:120],
                }
                print(json.dumps(sample, ensure_ascii=False, indent=2))
    finally:
        await service.stop()

    print(f"\n✅ Разом: {total} оголошень з {len(channels)} каналів")
    return 0 if total > 0 else 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Telegram channel parser")
    parser.add_argument("--limit", type=int, default=10, help="Messages per channel")
    parser.add_argument("--channel", action="append", dest="channels", help="Single channel to test")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Очистити dedupe перед тестом (інакше повторний запуск дає 0)",
    )
    args = parser.parse_args()

    channels = args.channels or settings.default_channels
    if not channels:
        print("❌ Немає каналів — задай TELEGRAM_CHANNELS у .env")
        sys.exit(1)

    code = asyncio.run(run(limit=args.limit, channels=channels, fresh=args.fresh))
    sys.exit(code)


if __name__ == "__main__":
    main()
