#!/usr/bin/env python3
"""Telegram channel parser worker (Telethon)."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings as app_settings  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.services.health import beat  # noqa: E402
from app.services.parser.settings import get_parser_settings  # noqa: E402
from app.services.telegram_channels.ingest import ingest_telegram_listing  # noqa: E402
from app.services.telegram_channels.service_loader import get_parser_channels, get_parser_service  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [telegram-worker] %(message)s")
logger = logging.getLogger("carbit.telegram_worker")


async def bootstrap_channels(service, channels: list[str], limit: int) -> None:
    for channel in channels:
        try:
            listings = await service.parse_channel_history(channel, limit=limit)
            logger.info("Bootstrap %s: %s listings", channel, len(listings))
            async with AsyncSessionLocal() as db:
                for listing in listings:
                    _, new_count, sent = await ingest_telegram_listing(db, listing, notify=True)
                    if new_count or sent:
                        logger.info("Linked %s: new=%s notifications=%s", listing.source_link, new_count, sent)
                await db.commit()
        except Exception:
            logger.exception("Bootstrap failed for %s", channel)


async def main() -> None:
    if not app_settings.TELEGRAM_ENABLED:
        logger.error("TELEGRAM_ENABLED=false — worker stopped")
        return
    if not app_settings.TELETHON_API_ID or not app_settings.TELETHON_API_HASH:
        logger.error("TELETHON_API_ID / TELETHON_API_HASH not configured")
        return

    channels = await get_parser_channels()
    if not channels:
        logger.error("No Telegram channels in DB — add them in admin /admin/channels")
        return

    parser_settings = await get_parser_settings()
    history_limit = int(parser_settings.get("telegram_history_limit", 100))

    service = get_parser_service()
    await service.start()
    logger.info("Telethon started, channels: %s", channels)

    await bootstrap_channels(service, channels, history_limit)
    await beat("telegram_worker")

    async def on_new_listing(listing) -> None:
        async with AsyncSessionLocal() as db:
            item, new_count, sent = await ingest_telegram_listing(db, listing, notify=True)
            await db.commit()
        await beat("telegram_worker")
        logger.info(
            "New listing %s | new=%s notifications=%s | %s",
            item.id,
            new_count,
            sent,
            item.title[:60],
        )

    async def heartbeat_loop() -> None:
        while True:
            await beat("telegram_worker")
            await asyncio.sleep(60)

    asyncio.create_task(heartbeat_loop())
    await service.listen(channels, on_new_listing)


if __name__ == "__main__":
    asyncio.run(main())
