"""Обробка черги keyword/photo для telegram_worker і fallback під час live-пошуку."""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.database import AsyncSessionLocal
from app.services.telegram_channels.bootstrap import ensure_parser_path
from app.services.telegram_channels.ingest import ingest_telegram_listing
from app.services.telegram_channels.lazy_photos import attach_photos_to_listing

logger = logging.getLogger(__name__)

PHOTO_QUEUE_MAX_ATTEMPTS = 4


def _photo_batch_limit(pending: int) -> int:
    return min(30, max(8, pending))


async def process_photo_queue(service, *, limit: int | None = None) -> int:
    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    store = ChannelMediaStore()
    pending = store.photo_queue_pending_count()
    if pending <= 0:
        return 0
    batch = limit if limit is not None else _photo_batch_limit(pending)
    jobs = store.claim_photo_jobs(limit=batch)
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
                    continue
                attempts = store.get_photo_attempts(listing_id)
                if attempts >= PHOTO_QUEUE_MAX_ATTEMPTS:
                    store.mark_photos_failed(listing_id)
                    logger.warning(
                        "Telegram photos failed after %s attempts: %s",
                        attempts,
                        listing_id,
                    )
            except Exception:
                logger.exception("Lazy photo job failed for %s", listing_id)
                attempts = store.get_photo_attempts(listing_id)
                if attempts >= PHOTO_QUEUE_MAX_ATTEMPTS:
                    store.mark_photos_failed(listing_id)
        await db.commit()
    return done


async def process_keyword_queue(service, *, limit: int = 16) -> int:
    """Scan / Telethon-search історії каналів з live-пошуку."""
    ensure_parser_path()
    from app.services.search.brand_model_keywords import (
        decode_telegram_keyword_job,
        decode_telegram_scan_job,
    )
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
                kw_payload = decode_telegram_keyword_job(query)
                if kw_payload:
                    listings = await service.search_channel_by_keywords(
                        channel,
                        kw_payload["q"],
                        limit=min(per_channel, 250),
                        brand=kw_payload.get("brand", ""),
                        model=kw_payload.get("model", ""),
                    )
                else:
                    # Зворотна сумісність: голий текстовий запит без пост-фільтра
                    listings = await service.search_channel_by_keywords(
                        channel,
                        query,
                        limit=min(per_channel, 250),
                    )
            async with AsyncSessionLocal() as db:
                from app.services.parser.settings import get_parser_settings

                parser_settings = await get_parser_settings()
                do_notify = bool(parser_settings.get("notify_telegram", True))
                for listing in listings:
                    item, _new, _sent, matched = await ingest_telegram_listing(
                        db,
                        listing,
                        notify=do_notify,
                        link_searches=True,
                        parser_service=service,
                    )
                    if matched and not item.images:
                        await attach_photos_to_listing(db, service, item.id)
                await db.commit()
            store.finish_keyword_job(job_id, found=len(listings))
            done += 1
            logger.info(
                "Keyword job %s %s q=%r → %s listings",
                job_id,
                channel,
                query[:40],
                len(listings),
            )
        except Exception as exc:
            logger.exception("Keyword search failed for %s q=%r", channel, query)
            store.finish_keyword_job(job_id, found=0, error=str(exc)[:300])
    return done


async def drain_keyword_jobs_for_ids(
    service,
    job_ids: list[int],
    *,
    wait_seconds: float,
) -> None:
    """Обробляє чергу, поки job_ids pending або не вичерпано wait_seconds."""
    if not job_ids:
        return

    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    store = ChannelMediaStore()
    deadline = time.monotonic() + max(0.5, float(wait_seconds))
    while time.monotonic() < deadline:
        if not store.keyword_jobs_pending(job_ids):
            return
        await process_keyword_queue(service, limit=16)
        await asyncio.sleep(0.35)


async def run_inline_keyword_refresh(
    job_ids: list[int],
    *,
    wait_seconds: float,
) -> None:
    """
    Fallback, коли telegram_worker не online: короткий Telethon у цьому процесі.
    Не використовувати, якщо worker тримає ту саму session (перевіряється в keyword_refresh).
    """
    from app.services.telegram_channels.service_loader import get_parser_service

    # skip_dedupe: keyword-пошук має ПЕРЕПАРСИТИ вже бачені пости —
    # інакше wrong brand (BMW Garage) лишається назавжди.
    service = get_parser_service(skip_dedupe=True)
    await service.start()
    try:
        await drain_keyword_jobs_for_ids(service, job_ids, wait_seconds=wait_seconds)
    finally:
        await service.stop()
