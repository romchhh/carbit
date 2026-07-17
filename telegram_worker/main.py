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
from app.services.telegram_channels.lazy_photos import attach_photos_to_listing  # noqa: E402
from app.services.telegram_channels.service_loader import get_parser_channels, get_parser_service  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [telegram-worker] %(message)s")
logger = logging.getLogger("carbit.telegram_worker")


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
                            "Linked %s: new=%s notifications=%s",
                            listing.source_link,
                            new_count,
                            sent,
                        )
                await db.commit()
        except Exception:
            logger.exception("Bootstrap failed for %s", channel)


async def process_photo_queue(service, *, limit: int = 5) -> int:
    from app.services.telegram_channels.bootstrap import ensure_parser_path

    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    jobs = ChannelMediaStore().claim_photo_jobs(limit=limit)
    if not jobs:
        return 0

    done = 0
    async with AsyncSessionLocal() as db:
        for listing_id in jobs:
            try:
                urls = await attach_photos_to_listing(db, service, listing_id)
                if urls:
                    done += 1
                    logger.info("Lazy photos %s: %s files", listing_id, len(urls))
            except Exception:
                logger.exception("Lazy photo job failed for %s", listing_id)
        await db.commit()
    return done


async def process_keyword_queue(service, *, limit: int = 4) -> int:
    """Scan історії Telegram-каналів за brand/model з live-пошуку."""
    from app.services.telegram_channels.bootstrap import ensure_parser_path

    ensure_parser_path()
    from app.services.search.brand_model_keywords import decode_telegram_scan_job
    from parser.channel_media_store import ChannelMediaStore

    store = ChannelMediaStore()
    jobs = store.claim_keyword_jobs(limit=limit)
    if not jobs:
        return 0

    done = 0
    for job in jobs:
        job_id = int(job["id"])
        query = str(job["query"])
        channel = str(job["channel"])
        per_channel = int(job.get("limit") or 500)
        try:
            payload = decode_telegram_scan_job(query)
            if payload:
                listings = await service.scan_channel_history_for_filters(
                    channel,
                    brand=payload["brand"],
                    model=payload.get("model", ""),
                    limit=per_channel,
                )
            else:
                listings = await service.search_channel_by_keywords(
                    channel,
                    query,
                    limit=min(per_channel, 100),
                )
            async with AsyncSessionLocal() as db:
                for listing in listings:
                    item, _new, _sent, matched = await ingest_telegram_listing(
                        db, listing, notify=False, link_searches=True
                    )
                    if matched and not item.images:
                        await attach_photos_to_listing(db, service, item.id)
                await db.commit()
            store.finish_keyword_job(job_id, found=len(listings))
            done += 1
            logger.info(
                "History scan %s brand=%r model=%r → %s listings",
                channel,
                payload["brand"] if payload else None,
                payload.get("model") if payload else query,
                len(listings),
            )
        except Exception as exc:
            logger.exception("Keyword search failed for %s q=%r", channel, query)
            store.finish_keyword_job(job_id, found=0, error=str(exc)[:300])
    return done


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
        while True:
            busy = False
            try:
                if await process_keyword_queue(service, limit=4):
                    busy = True
            except Exception:
                logger.exception("Keyword queue tick failed")
            try:
                if await process_photo_queue(service, limit=5):
                    busy = True
            except Exception:
                logger.exception("Photo queue tick failed")
            await beat("telegram_worker")
            await asyncio.sleep(1 if busy else 4)

    asyncio.create_task(heartbeat_loop())
    await service.listen(channels, on_new_listing)


if __name__ == "__main__":
    asyncio.run(main())
