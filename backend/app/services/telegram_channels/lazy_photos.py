"""Lazy download Telegram photos and attach to Listing.images."""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, Source
from app.services.telegram.media_urls import filter_existing_image_urls
from app.services.telegram_channels.bootstrap import ensure_parser_path
from app.services.telegram_channels.channel_paths import telegram_channel_media_slug
from app.services.telegram_channels.mapper import telegram_media_url

if TYPE_CHECKING:
    from parser.service import CarParserService

logger = logging.getLogger(__name__)

PHOTO_WAIT_INTERVAL = 0.35
PHOTO_PAGE_WAIT_SECONDS = 18.0
PHOTO_SEARCH_WAIT_SECONDS = 0.0

# Скільки не смикати Telethon після відмови (розлогінена сесія, обрив).
TELETHON_RETRY_AFTER_SECONDS = 120.0

_service_lock = asyncio.Lock()
_shared_service: "CarParserService | None" = None
_telethon_blocked_until = 0.0
_telethon_block_reason = ""
_inflight_downloads: dict[str, asyncio.Task] = {}


def telethon_unavailable_reason() -> str:
    """Причина, чому фото зараз не завантажити (для UI), або порожній рядок."""
    return _telethon_block_reason if _telethon_blocked() else ""


def _block_telethon(reason: str) -> None:
    global _telethon_blocked_until, _telethon_block_reason
    _telethon_blocked_until = time.monotonic() + TELETHON_RETRY_AFTER_SECONDS
    _telethon_block_reason = reason
    logger.warning("Telethon недоступний (%s), пауза %.0fс", reason, TELETHON_RETRY_AFTER_SECONDS)


def _telethon_blocked() -> bool:
    return time.monotonic() < _telethon_blocked_until


async def _acquire_shared_service():
    """Один Telethon-клієнт на процес: start/stop на кожен запит коштує секунди."""
    global _shared_service
    if _telethon_blocked():
        return None
    async with _service_lock:
        if _telethon_blocked():
            return None
        if _shared_service is not None:
            return _shared_service
        from app.services.telegram_channels.service_loader import get_parser_service

        service = get_parser_service(skip_dedupe=True)
        try:
            await asyncio.wait_for(service.start(), timeout=20.0)
        except Exception as exc:  # включно з TelegramNotAuthorizedError
            _block_telethon(type(exc).__name__)
            try:
                await service.stop()
            except Exception:
                pass
            return None
        _shared_service = service
        return _shared_service


async def _drop_shared_service() -> None:
    global _shared_service
    async with _service_lock:
        service, _shared_service = _shared_service, None
    if service is not None:
        try:
            await service.stop()
        except Exception:
            logger.exception("Telethon stop")


async def close_shared_photo_service() -> None:
    """Викликається на shutdown застосунку."""
    await _drop_shared_service()


async def _download_photos_once(
    listing_id: str,
    channel: str,
    message_ids: list[int],
    *,
    limit: int,
    timeout: float,
) -> list[str]:
    """Качає файли, склеюючи паралельні запити одного оголошення в одну задачу."""
    existing = _inflight_downloads.get(listing_id)
    if existing is not None and not existing.done():
        try:
            return await asyncio.wait_for(asyncio.shield(existing), timeout=timeout)
        except Exception:
            return []

    async def _run() -> list[str]:
        service = await _acquire_shared_service()
        if service is None:
            return []
        try:
            return await service.download_listing_photos(
                listing_id,
                channel,
                message_ids,
                max_photos=limit,
            )
        except Exception as exc:
            logger.exception("Telegram photo download failed for %s", listing_id)
            # Клієнт міг лишитись у неробочому стані — піднімемо новий.
            await _drop_shared_service()
            _block_telethon(type(exc).__name__)
            return []

    task = asyncio.create_task(_run())
    _inflight_downloads[listing_id] = task
    task.add_done_callback(lambda t: _inflight_downloads.pop(listing_id, None))
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("Telegram photo download timed out for %s", listing_id)
        return []


def _photo_refs_for(listing_id: str) -> tuple[str, list[int]] | None:
    refs = _media_store().get_photo_refs(listing_id)
    if refs:
        channel, message_ids, _status = refs
        if message_ids:
            return channel, message_ids
    body = listing_id.removeprefix("telegram_")
    channel_part, _, msg_part = body.rpartition("_")
    if channel_part and msg_part.isdigit():
        return f"@{channel_part}", [int(msg_part)]
    return None


def _media_store():
    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    return ChannelMediaStore()


def _urls_from_existing_files(channel: str, message_ids: list[int], *, limit: int) -> list[str]:
    """Якщо jpg уже лежать у media/ — підставляємо URL без Telethon."""
    from app.core.config import settings

    safe = telegram_channel_media_slug(channel)
    root = Path(settings.TELEGRAM_MEDIA_DIR) / safe
    urls: list[str] = []
    for msg_id in message_ids:
        if len(urls) >= limit:
            break
        path = root / f"{int(msg_id)}.jpg"
        if path.is_file() and path.stat().st_size > 0:
            url = telegram_media_url(str(path))
            if url:
                urls.append(url)
    return urls


def load_existing_telegram_photo_urls(listing_id: str, *, limit: int = 1) -> list[str]:
    """URL з уже скачаних jpg (без Telethon) — для TG-сповіщень."""
    refs = _media_store().get_photo_refs(listing_id)
    if refs:
        channel, message_ids, _status = refs
        return _urls_from_existing_files(channel, message_ids, limit=max(1, limit))

    body = listing_id.removeprefix("telegram_")
    channel_part, _, msg_part = body.rpartition("_")
    if channel_part and msg_part.isdigit():
        return _urls_from_existing_files(
            f"@{channel_part}",
            [int(msg_part)],
            limit=max(1, limit),
        )
    return []


async def attach_photos_to_listing(
    db: AsyncSession,
    service: "CarParserService",
    listing_id: str,
    *,
    max_photos: int | None = None,
) -> list[str]:
    """Завантажує фото через Telethon і пише URL у Listing.images."""
    from app.core.config import settings

    listing = await db.get(Listing, listing_id)
    if not listing:
        return []
    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    if source != Source.telegram.value and source != "telegram":
        return list(listing.images or [])

    kept = filter_existing_image_urls(listing.images)
    if kept:
        if kept != list(listing.images or []):
            listing.images = kept
            await db.flush()
        _media_store().mark_photos_done(listing_id)
        return kept
    if listing.images:
        # URL в БД, файлів уже немає — скидаємо і качаємо знову
        listing.images = []
        await db.flush()

    refs = _media_store().get_photo_refs(listing_id)
    if not refs:
        # Fallback: telegram_{channel}_{message_id}
        body = listing_id.removeprefix("telegram_")
        channel_part, _, msg_part = body.rpartition("_")
        if not channel_part or not msg_part.isdigit():
            _media_store().mark_photos_failed(listing_id)
            return []
        channel = f"@{channel_part}"
        message_ids = [int(msg_part)]
    else:
        channel, message_ids, status = refs
        if status == "done" and listing.images:
            return list(listing.images)

    # Хоча б 1 фото для картки; більше — якщо TELEGRAM_MAX_PHOTOS дозволяє
    limit = max(1, max_photos if max_photos is not None else settings.TELEGRAM_MAX_PHOTOS)
    # Спочатку перевіряємо вже скачані файли — без повторного Telethon
    urls = _urls_from_existing_files(channel, message_ids, limit=limit)
    if not urls:
        try:
            paths = await service.download_listing_photos(
                listing_id,
                channel,
                message_ids,
                max_photos=limit,
            )
        except Exception:
            logger.exception("Photo download failed for %s", listing_id)
            return []
        urls = [telegram_media_url(p) for p in paths[:limit]]
        urls = [u for u in urls if u]

    if urls:
        listing.images = urls
        await db.flush()
        _media_store().mark_photos_done(listing_id)
    else:
        logger.warning("Telegram photos not ready yet for %s", listing_id)
    return urls


def _ensure_photo_refs(listing_id: str) -> bool:
    """Гарантує наявність refs (для старих записів — з listing_id)."""
    store = _media_store()
    if store.get_photo_refs(listing_id):
        return True
    body = listing_id.removeprefix("telegram_")
    channel_part, _, msg_part = body.rpartition("_")
    if not channel_part or not msg_part.isdigit():
        return False
    store.save_photo_refs(listing_id, f"@{channel_part}", [int(msg_part)])
    return True


def enqueue_listing_photos(
    listing_id: str,
    *,
    priority: int = 0,
    force: bool = False,
) -> bool:
    if not _ensure_photo_refs(listing_id):
        return False
    return _media_store().enqueue_photo_download(
        listing_id,
        priority=priority,
        force=force,
    )


async def telegram_worker_online() -> bool:
    from app.services.telegram_channels.telethon_auth import _worker_online

    return await _worker_online()


def listing_needs_photos(listing: Listing) -> bool:
    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    if source not in ("telegram", Source.telegram.value):
        return False
    if filter_existing_image_urls(listing.images):
        return False
    if load_existing_telegram_photo_urls(listing.id, limit=1):
        return False
    return True


async def sync_telegram_photos_from_disk(
    db: AsyncSession,
    listing: Listing,
    *,
    max_photos: int = 1,
) -> list[str]:
    """Якщо jpg уже на диску — пише URL у Listing.images без Telethon."""
    kept = filter_existing_image_urls(listing.images)
    if kept:
        if kept != list(listing.images or []):
            listing.images = kept
            await db.flush()
        return kept
    if listing.images:
        listing.images = []
        await db.flush()
    urls = load_existing_telegram_photo_urls(listing.id, limit=max(1, max_photos))
    if not urls:
        return []
    listing.images = urls
    await db.flush()
    _media_store().mark_photos_done(listing.id)
    return urls


async def backfill_telegram_photos(
    db: AsyncSession,
    service: "CarParserService",
    *,
    limit: int = 40,
) -> int:
    """Догружає фото для TG-оголошень без images (cron / worker)."""
    from sqlalchemy import select

    from app.services.telegram_channels.freshness import telegram_published_cutoff

    rows = await db.scalars(
        select(Listing)
        .where(Listing.source == Source.telegram)
        .where(Listing.published_at >= telegram_published_cutoff())
        .order_by(Listing.published_at.desc())
        .limit(max(limit * 4, limit))
    )
    done = 0
    for listing in rows.all():
        if done >= limit:
            break
        if filter_existing_image_urls(listing.images):
            continue
        urls = await sync_telegram_photos_from_disk(db, listing, max_photos=1)
        if urls:
            done += 1
            continue
        if not listing_needs_photos(listing):
            continue
        urls = await attach_photos_to_listing(db, service, listing.id, max_photos=1)
        if urls:
            done += 1
    return done


async def refresh_listing_photo_urls(
    db: AsyncSession,
    listing_id: str,
    *,
    max_photos: int = 1,
) -> list[str]:
    db.expire_all()
    listing = await db.get(Listing, listing_id)
    if not listing:
        return []
    kept = filter_existing_image_urls(listing.images)
    if kept:
        if kept != list(listing.images or []):
            listing.images = kept
            await db.flush()
        return kept
    return await sync_telegram_photos_from_disk(db, listing, max_photos=max_photos)


async def wait_for_listing_photos(
    db: AsyncSession,
    listing_id: str,
    *,
    timeout: float = PHOTO_PAGE_WAIT_SECONDS,
) -> list[str]:
    """Чекає поки worker запише images у БД (для ensure-photos)."""
    deadline = asyncio.get_running_loop().time() + max(0.5, timeout)
    while asyncio.get_running_loop().time() < deadline:
        urls = await refresh_listing_photo_urls(db, listing_id)
        if urls:
            return urls
        await asyncio.sleep(PHOTO_WAIT_INTERVAL)
    return await refresh_listing_photo_urls(db, listing_id)


async def ensure_telegram_listing_photos(
    db: AsyncSession,
    listing: Listing,
    *,
    max_photos: int = 1,
    try_telethon: bool = True,
    telethon_timeout: float = 25.0,
) -> list[str]:
    """Підставляє фото з диску або завантажує через Telethon (мінімум 1 для картки)."""
    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    if source not in ("telegram", Source.telegram.value):
        return list(listing.images or [])

    urls = await sync_telegram_photos_from_disk(db, listing, max_photos=max_photos)
    if urls:
        return urls

    if not listing_needs_photos(listing):
        return list(listing.images or [])

    # force: файлів на диску немає, тож статус 'done' у refs застарілий.
    enqueue_listing_photos(listing.id, priority=2, force=True)
    worker_up = await telegram_worker_online()

    if worker_up:
        urls = await wait_for_listing_photos(
            db,
            listing.id,
            timeout=min(telethon_timeout, 28.0),
        )
        if urls:
            return urls
        enqueue_listing_photos(listing.id, priority=3, force=True)
        urls = await wait_for_listing_photos(
            db,
            listing.id,
            timeout=min(12.0, max(4.0, telethon_timeout * 0.45)),
        )
        if urls:
            return urls
        return list(listing.images or [])

    if try_telethon and not _telethon_blocked():
        refs = _photo_refs_for(listing.id)
        if refs:
            channel, message_ids = refs
            paths = await _download_photos_once(
                listing.id,
                channel,
                message_ids,
                limit=max(1, max_photos),
                timeout=max(4.0, min(telethon_timeout, 22.0)),
            )
            if paths:
                urls = await sync_telegram_photos_from_disk(
                    db,
                    listing,
                    max_photos=max_photos,
                )
                if urls:
                    return urls

    return list(listing.images or [])


async def hydrate_telegram_page_photos(
    db: AsyncSession,
    items: list,
    *,
    max_downloads: int = 20,
    telethon_timeout: float = 25.0,
    wait_seconds: float = 0.0,
) -> list:
    """Сторінка каталогу: диск → enqueue; wait_seconds>0 лише для ensure-photos."""
    from app.schemas.schemas import ListingOut

    if not items:
        return items

    updated: dict[str, list[str]] = {}
    need_download: list[Listing] = []

    for item in items:
        if not isinstance(item, ListingOut):
            continue
        if (item.source or "").lower() != "telegram":
            continue
        if filter_existing_image_urls(item.images):
            continue
        listing = await db.get(Listing, item.id)
        if not listing:
            continue
        urls = await sync_telegram_photos_from_disk(db, listing, max_photos=1)
        if urls:
            updated[item.id] = urls
        elif listing_needs_photos(listing):
            need_download.append(listing)

    if not need_download:
        return _apply_photo_updates(items, updated)

    worker_up = await telegram_worker_online()
    targets = need_download[: max(1, max_downloads)]

    for listing in targets:
        enqueue_listing_photos(listing.id, priority=1, force=True)

    if worker_up and wait_seconds > 0:
        pending_ids = {listing.id for listing in targets}
        deadline = asyncio.get_running_loop().time() + max(2.0, wait_seconds)
        while pending_ids and asyncio.get_running_loop().time() < deadline:
            for listing_id in list(pending_ids):
                urls = await refresh_listing_photo_urls(db, listing_id)
                if urls:
                    updated[listing_id] = urls
                    pending_ids.discard(listing_id)
            if pending_ids:
                await asyncio.sleep(PHOTO_WAIT_INTERVAL)
    elif not worker_up and not _telethon_blocked():
        deadline = asyncio.get_running_loop().time() + max(5.0, telethon_timeout)
        for listing in targets:
            left = deadline - asyncio.get_running_loop().time()
            if left <= 0.5 or _telethon_blocked():
                break
            refs = _photo_refs_for(listing.id)
            if not refs:
                continue
            channel, message_ids = refs
            paths = await _download_photos_once(
                listing.id,
                channel,
                message_ids,
                limit=1,
                timeout=min(left, 12.0),
            )
            if not paths:
                continue
            urls = await sync_telegram_photos_from_disk(db, listing, max_photos=1)
            if urls:
                updated[listing.id] = urls

    return _apply_photo_updates(items, updated)


def _apply_photo_updates(items: list, updated: dict[str, list[str]]) -> list:
    if not updated:
        return items
    out: list = []
    for item in items:
        urls = updated.get(getattr(item, "id", ""))
        if not urls:
            out.append(item)
            continue
        sd = dict(getattr(item, "source_data", None) or {})
        sd.pop("photos_pending", None)
        out.append(
            item.model_copy(
                update={
                    "images": urls,
                    "source_data": sd or None,
                }
            )
        )
    return out
