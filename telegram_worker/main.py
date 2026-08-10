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
from app.services.telegram_channels.keyword_jobs import (  # noqa: E402
    process_keyword_queue,
    process_photo_queue,
)
from app.services.telegram_channels.lazy_photos import backfill_telegram_photos  # noqa: E402
from app.services.telegram_channels.service_loader import get_parser_channels, get_parser_service  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [telegram-worker] %(message)s")
logger = logging.getLogger("carbit.telegram_worker")


def _poll_sleep_seconds(settings: dict, *, busy: bool, photo_backlog: int = 0) -> float:
    poll = max(1, int(settings.get("telegram_worker_poll_seconds") or 3))
    if photo_backlog > 0:
        return 0.25 if busy else 0.6
    return 0.5 if busy else float(poll)


def _channel_sync_seconds(settings: dict) -> float:
    return float(max(15, int(settings.get("telegram_channel_sync_seconds") or 45)))


async def bootstrap_channels(service, channels: list[str], limit: int) -> None:
    for channel in channels:
        try:
            listings = await service.parse_channel_history(channel, limit=limit)
            stats = getattr(service, "last_parse_stats", {}) or {}
            logger.info(
                "Bootstrap %s: %s listings (msgs=%s cursor %s→%s)",
                channel,
                len(listings),
                stats.get("messages"),
                stats.get("cursor_from"),
                stats.get("cursor_to"),
            )
            async with AsyncSessionLocal() as db:
                for listing in listings:
                    item, new_count, sent, matched = await ingest_telegram_listing(
                        db, listing, notify=True, parser_service=service
                    )
                    if new_count or sent:
                        logger.info(
                            "Linked %s: new=%s notifications=%s matched=%s",
                            listing.source_link,
                            new_count,
                            sent,
                            matched,
                        )
                await db.commit()
        except Exception:
            logger.exception("Bootstrap failed for %s", channel)


async def channel_sync_loop(
    service,
    *,
    history_limit: int,
    bootstrapped: set[str],
) -> None:
    """Підхоплює нові канали з БД без перезапуску worker."""
    while True:
        settings = await get_parser_settings()
        await asyncio.sleep(_channel_sync_seconds(settings))
        try:
            channels = await get_parser_channels()
            new = [ch for ch in channels if ch not in bootstrapped]
            if new:
                logger.info("Нові канали з адмінки: %s", new)
                await bootstrap_channels(service, new, max(history_limit, 500))
                bootstrapped.update(new)
            await service.sync_monitored_channels(channels)
        except Exception:
            logger.exception("Channel sync tick failed")


async def bootstrap_background(
    service,
    channels: list[str],
    *,
    bootstrap_limit: int,
    bootstrapped: set[str],
) -> None:
    try:
        await bootstrap_channels(service, channels, bootstrap_limit)
        bootstrapped.update(channels)
        logger.info("Bootstrap finished for %s channel(s)", len(channels))
    except Exception:
        logger.exception("Background bootstrap failed")


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
    history_limit = max(100, int(parser_settings.get("telegram_history_limit", 500)))
    bootstrap_limit = max(history_limit, 500)

    service = get_parser_service()
    await service.start()
    await beat("telegram_worker")
    try:
        me = await service.client.get_me()
        from parser.session_meta import write_session_meta

        write_session_meta(
            user_id=me.id,
            first_name=me.first_name or "",
            username=me.username,
            source="telegram_worker",
        )
    except Exception:
        logger.exception("Failed to write Telethon session meta")
    logger.info("Telethon started, channels: %s", channels)

    bootstrapped: set[str] = set()
    asyncio.create_task(
        bootstrap_background(
            service,
            channels,
            bootstrap_limit=bootstrap_limit,
            bootstrapped=bootstrapped,
        )
    )

    async def on_new_listing(listing) -> None:
        async with AsyncSessionLocal() as db:
            item, new_count, sent, matched = await ingest_telegram_listing(
                db, listing, notify=True, parser_service=service
            )
            await db.commit()
        await beat("telegram_worker")
        logger.info(
            "New listing %s | new=%s notifications=%s matched=%s photos=%s | %s",
            item.id,
            new_count,
            sent,
            matched,
            len(item.images or []),
            item.title[:60],
        )

    async def heartbeat_loop() -> None:
        from app.services.telegram_channels.bootstrap import ensure_parser_path
        from app.services.telegram_channels.purge import purge_stale_telegram_listings

        ensure_parser_path()
        from parser.channel_media_store import ChannelMediaStore

        store = ChannelMediaStore()
        last_purge_mono = 0.0
        while True:
            settings = await get_parser_settings()
            # Чистимо jobs, що застрягли (crash попереднього циклу)
            try:
                stuck = store.reset_stuck_running_jobs(older_than_seconds=180)
                if stuck:
                    logger.warning("Reset %s stuck running keyword jobs", stuck)
            except Exception:
                pass
            busy = False
            photo_pending = store.photo_queue_pending_count()
            try:
                if photo_pending > 0:
                    if await process_photo_queue(service):
                        busy = True
            except Exception:
                logger.exception("Photo queue tick failed")
            try:
                keyword_limit = 8 if photo_pending > 40 else 16
                if await process_keyword_queue(service, limit=keyword_limit):
                    busy = True
            except Exception:
                logger.exception("Keyword queue tick failed")

            try:
                async with AsyncSessionLocal() as db:
                    filled = await backfill_telegram_photos(db, service, limit=12)
                    if filled:
                        await db.commit()
                        busy = True
                        logger.info("Telegram photo backfill: %s listings", filled)
            except Exception:
                logger.exception("Telegram photo backfill tick failed")

            # Раз на годину — видаляємо TG-лоти старші за 3 місяці.
            now_mono = asyncio.get_event_loop().time()
            if now_mono - last_purge_mono >= 3600:
                try:
                    async with AsyncSessionLocal() as db:
                        purged = await purge_stale_telegram_listings(db)
                        await db.commit()
                    if purged:
                        logger.info("Purged %s stale Telegram listings (>3 months)", purged)
                    last_purge_mono = now_mono
                except Exception:
                    logger.exception("Telegram stale purge failed")

            await beat("telegram_worker")
            await asyncio.sleep(
                _poll_sleep_seconds(settings, busy=busy, photo_backlog=photo_pending)
            )

    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(
        channel_sync_loop(service, history_limit=history_limit, bootstrapped=bootstrapped)
    )
    await service.listen(channels, on_new_listing)


if __name__ == "__main__":
    asyncio.run(main())
