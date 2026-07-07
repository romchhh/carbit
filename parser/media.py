"""
Завантаження фото з повідомлень (в т.ч. альбомів - кілька фото в одному оголошенні).
"""
import os
from telethon import TelegramClient
from telethon.tl.types import Message

from .config import settings


def _channel_dir(channel: str) -> str:
    safe = channel.strip("@").replace("/", "_")
    path = os.path.join(settings.media_dir, safe)
    os.makedirs(path, exist_ok=True)
    return path


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
    За замовчуванням — не більше settings.max_photos_per_listing (5).
    """
    limit = max_photos if max_photos is not None else settings.max_photos_per_listing
    paths = []
    out_dir = _channel_dir(channel)
    for msg in messages:
        if len(paths) >= limit:
            break
        if not isinstance(msg, Message):
            continue
        if not msg.photo and not (msg.media and getattr(msg.media, "photo", None)):
            continue
        filename = f"{msg.id}.jpg"
        full_path = os.path.join(out_dir, filename)
        if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
            paths.append(full_path)
            continue
        try:
            saved = await client.download_media(msg, file=full_path)
            if saved:
                paths.append(saved)
        except Exception:
            continue
    return paths