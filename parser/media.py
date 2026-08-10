"""
Завантаження фото з повідомлень (в т.ч. альбомів - кілька фото в одному оголошенні).
"""
from __future__ import annotations

import logging
import os
from telethon import TelegramClient
from telethon.tl.types import Message

from .config import settings

from .media_compress import compress_jpeg

log = logging.getLogger("carbit_parser.media")


def _maybe_compress(path: str) -> None:
    compress_jpeg(
        path,
        max_width=settings.media_max_width,
        quality=settings.media_jpeg_quality,
    )


def _channel_dir(channel: str) -> str:
    safe = channel.strip("@").replace("/", "_").replace(" ", "_")
    path = os.path.join(settings.media_dir, safe)
    os.makedirs(path, exist_ok=True)
    return path


def _has_photo(msg: Message | None) -> bool:
    if not msg or not isinstance(msg, Message):
        return False
    if msg.photo or (msg.media and getattr(msg.media, "photo", None)):
        return True
    # Багато каналів шлють стиснені фото як document (image/jpeg)
    doc = getattr(msg, "document", None)
    if doc is None and msg.media is not None:
        doc = getattr(msg.media, "document", None)
    mime = (getattr(doc, "mime_type", None) or "") if doc else ""
    return bool(mime.startswith("image/"))


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
    За замовчуванням — не більше settings.max_photos_per_listing (1).
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
            _maybe_compress(full_path)
            paths.append(full_path)
            continue
        try:
            saved = await client.download_media(msg, file=full_path)
            if saved:
                _maybe_compress(str(saved))
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

    async def _expand_album(primary: Message) -> list[Message]:
        album: list[Message] = []
        async for msg in client.iter_messages(
            entity,
            min_id=max(primary.id - 40, 0),
            max_id=primary.id + 40,
        ):
            if msg.grouped_id == primary.grouped_id and _has_photo(msg):
                album.append(msg)
        album.sort(key=lambda m: m.id)
        return album

    # Альбом: текст часто на окремому msg без фото — розгортаємо групу навіть для 1 фото.
    if ordered:
        primary = ordered[0]
        if primary.grouped_id:
            has_photo = any(_has_photo(m) for m in ordered)
            if not has_photo or (limit > 1 and len(ordered) == 1):
                album = await _expand_album(primary)
                if album:
                    ordered = album

    paths = await download_photos(client, channel, ordered, max_photos=limit)
    if paths:
        return paths

    # Reply-ланцюг: текст у пості, фото в reply (без grouped_id).
    primary_id = ids[0]
    for msg in fetched:
        if not isinstance(msg, Message) or not _has_photo(msg):
            continue
        reply_to = getattr(getattr(msg, "reply_to", None), "reply_to_msg_id", None)
        if reply_to in ids or msg.id in ids:
            extra = await download_photos(client, channel, [msg], max_photos=limit)
            if extra:
                return extra

    neighbor_ids = [mid for mid in range(primary_id - 4, primary_id + 5) if mid > 0 and mid not in by_id]
    if neighbor_ids:
        extra_msgs = await client.get_messages(entity, ids=neighbor_ids[:12])
        if not isinstance(extra_msgs, list):
            extra_msgs = [extra_msgs] if extra_msgs else []
        for msg in sorted(
            (m for m in extra_msgs if isinstance(m, Message) and _has_photo(m)),
            key=lambda m: abs(m.id - primary_id),
        ):
            reply_to = getattr(getattr(msg, "reply_to", None), "reply_to_msg_id", None)
            if reply_to == primary_id or abs(msg.id - primary_id) <= 1:
                extra = await download_photos(client, channel, [msg], max_photos=limit)
                if extra:
                    return extra

    return []
