"""Lazy download Telegram photos and attach to Listing.images."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, Source
from app.services.telegram_channels.bootstrap import ensure_parser_path
from app.services.telegram_channels.mapper import telegram_media_url

if TYPE_CHECKING:
    from parser.service import CarParserService

logger = logging.getLogger(__name__)


def _media_store():
    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    return ChannelMediaStore()


def _urls_from_existing_files(channel: str, message_ids: list[int], *, limit: int) -> list[str]:
    """Якщо jpg уже лежать у media/ — підставляємо URL без Telethon."""
    from app.core.config import settings

    safe = channel.strip("@").replace("/", "_").replace(" ", "_")
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

    if listing.images:
        _media_store().mark_photos_done(listing_id)
        return list(listing.images)

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
        if status == "done":
            return list(listing.images or [])

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
            _media_store().mark_photos_failed(listing_id)
            return []
        urls = [telegram_media_url(p) for p in paths[:limit]]
        urls = [u for u in urls if u]

    if urls:
        listing.images = urls
        await db.flush()
        _media_store().mark_photos_done(listing_id)
    else:
        _media_store().mark_photos_failed(listing_id)
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


def enqueue_listing_photos(listing_id: str) -> bool:
    if not _ensure_photo_refs(listing_id):
        return False
    return _media_store().enqueue_photo_download(listing_id)


def listing_needs_photos(listing: Listing) -> bool:
    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    if source not in ("telegram", Source.telegram.value):
        return False
    if listing.images:
        return False
    refs = _media_store().get_photo_refs(listing.id)
    if refs and refs[2] == "done":
        return False
    return True
