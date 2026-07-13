"""
Завантаження фото з повідомлень (в т.ч. альбомів - кілька фото в одному оголошенні).
"""
from __future__ import annotations

import logging
import os
from telethon import TelegramClient
from telethon.tl.types import Message

from .config import settings

log = logging.getLogger("carbit_parser.media")


def _channel_dir(channel: str) -> str:
    safe = channel.strip("@").replace("/", "_")
    path = os.path.join(settings.media_dir, safe)
    os.makedirs(path, exist_ok=True)
    return path


def _has_photo(msg: Message | None) -> bool:
    if not msg or not isinstance(msg, Message):
        return False
    return bool(msg.photo or (msg.media and getattr(msg.media, "photo", None)))


async def download_photos(
    client: TelegramClient,
    channel: str,
    messages: list,
    *,
    max_photos: int | None = None,
) -> list:
    """
    messages - список Telethon Message з одного оголошення (може бути 1 або кілька,
    якщо це альбом). Повертає список локальних шляхів до збережених фото.
    За замовчуванням — не більше settings.max_photos_per_listing (3).
    """
    limit = max_photos if max_photos is not None else settings.max_photos_per_listing
    paths: list[str] = []
    out_dir = _channel_dir(channel)
    for msg in messages:
        if len(paths) >= limit:
            break
        if not _has_photo(msg):
            continue
        filename = f"{msg.id}.jpg"
        full_path = os.path.join(out_dir, filename)
        if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
            paths.append(full_path)
            continue
        try:
            saved = await client.download_media(msg, file=full_path)
            if saved:
                paths.append(str(saved))
        except Exception as exc:
            log.warning(
                "Не вдалось завантажити фото msg=%s channel=%s: %s",
                getattr(msg, "id", "?"),
                channel,
                exc,
            )
            continue
    return paths


async def download_photos_by_ids(
    client: TelegramClient,
    channel: str,
    message_ids: list[int],
    *,
    max_photos: int | None = None,
) -> list[str]:
    """Lazy download: тягнемо повідомлення по id і зберігаємо ≤ max_photos фото."""
    limit = max_photos if max_photos is not None else settings.max_photos_per_listing
    ids = [int(x) for x in message_ids if x][: max(limit * 3, limit)]
    if not ids:
        return []

    try:
        entity = await client.get_entity(channel)
    except Exception as exc:
        log.warning("Не вдалось отримати entity %s для фото: %s", channel, exc)
        return []

    fetched = await client.get_messages(entity, ids=ids)
    if not isinstance(fetched, list):
        fetched = [fetched] if fetched else []

    # Зберігаємо порядок як у message_ids
    by_id = {m.id: m for m in fetched if isinstance(m, Message)}
    ordered = [by_id[mid] for mid in ids if mid in by_id]

    # Якщо прийшов лише primary з альбому — підтягнемо сусідів з тим самим grouped_id
    if len(ordered) == 1 and ordered[0].grouped_id:
        album: list[Message] = []
        primary = ordered[0]
        async for msg in client.iter_messages(
            entity,
            min_id=max(primary.id - 40, 0),
            max_id=primary.id + 40,
        ):
            if msg.grouped_id == primary.grouped_id and _has_photo(msg):
                album.append(msg)
        album.sort(key=lambda m: m.id)
        if album:
            ordered = album

    return await download_photos(client, channel, ordered, max_photos=limit)
