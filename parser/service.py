"""
CarParserService - головна точка входу в модуль.

Використання (як бібліотека всередині твого застосунку):

    from service import CarParserService

    service = CarParserService()
    await service.start()

    # 1. Разовий парсинг історії каналу
    listings = await service.parse_channel_history("@ua_autobazar", limit=200)

    # 2. Постійне прослуховування нових оголошень у реальному часі
    async def on_new_car(listing):
        print(listing.to_dict())

    await service.listen(["@ua_autobazar", "@CarsBidPro"], on_new_car)
"""
import asyncio
import logging
from datetime import datetime
from typing import Callable, Awaitable, Optional

from telethon import events
from telethon.tl.types import Message
from telethon.utils import get_peer_id

from .channel_links import is_numeric_channel_id, public_telegram_message_url

from .config import settings
from .telegram_client import build_client, ensure_joined
from .extractor import extract_car_data, is_valid_car_listing
from .media import download_photos_by_ids
from .dedupe import DedupeStore
from .channel_media_store import ChannelMediaStore
from .models import CarListing

log = logging.getLogger("carbit_parser.service")
logging.basicConfig(level=logging.INFO)


class CarParserService:
    def __init__(self, *, fresh_dedupe: bool = False, skip_dedupe: bool = False):
        self.client = build_client()
        self.dedupe = DedupeStore()
        self.media_store = ChannelMediaStore()
        if fresh_dedupe:
            self.dedupe.clear()
        self.skip_dedupe = skip_dedupe
        self._joined_cache = set()
        self._slug_cache: dict[str, str] = {}
        self.last_parse_stats: dict = {}

    async def start(self):
        for name in ("telethon", "telethon.network", "telethon.client"):
            logging.getLogger(name).setLevel(logging.WARNING)
        await self.client.start(phone=settings.phone or None)
        log.info("Telethon клієнт запущено")

    async def stop(self):
        await self.client.disconnect()

    async def _ensure_joined_cached(self, channel: str) -> bool:
        if channel in self._joined_cache:
            return True
        ok = await ensure_joined(self.client, channel)
        if ok:
            self._joined_cache.add(channel)
        return ok

    async def _channel_public_slug(self, channel: str) -> str:
        """Повертає публічний username каналу (без @) для t.me/посилань."""
        key = channel.strip()
        if key in self._slug_cache:
            return self._slug_cache[key]

        slug = key.lstrip("@")
        if not is_numeric_channel_id(slug):
            self._slug_cache[key] = slug
            return slug

        try:
            entity = await self.client.get_entity(int(slug) if slug.startswith("-") else slug)
            username = getattr(entity, "username", None)
            if username:
                slug = username
        except Exception as exc:
            log.warning("Не вдалось отримати username для %s: %s", channel, exc)

        self._slug_cache[key] = slug
        return slug

    async def _normalize_channel(self, channel: str) -> str:
        slug = await self._channel_public_slug(channel)
        return f"@{slug}"

    async def _build_source_link(self, channel: str, message_id: int) -> str:
        slug = await self._channel_public_slug(channel)
        return public_telegram_message_url(slug, message_id)

    def _merge_group_text(self, group_messages: list) -> str:
        parts: list[str] = []
        for msg in group_messages:
            chunk = (msg.text or "").strip()
            if chunk and chunk not in parts:
                parts.append(chunk)
        return "\n".join(parts)

    async def _process_group(self, channel: str, group_messages: list) -> Optional[CarListing]:
        """group_messages - список Message з однаковим grouped_id (або 1 повідомлення).

        Фото НЕ качаємо тут (lazy): лише валідуємо текст і зберігаємо refs.
        """
        channel = await self._normalize_channel(channel)
        group_messages = sorted(group_messages, key=lambda m: m.id)
        primary = next((m for m in group_messages if (m.text or "").strip()), group_messages[0])
        text = self._merge_group_text(group_messages)
        ids = [m.id for m in group_messages]
        max_id = max(ids) if ids else 0

        if not text.strip() and not any(m.photo for m in group_messages):
            self.last_parse_stats["empty"] = self.last_parse_stats.get("empty", 0) + 1
            if max_id:
                self.media_store.advance_cursor(channel, max_id)
            return None

        if not self.skip_dedupe and self.dedupe.is_seen(channel, primary.id):
            self.last_parse_stats["dedupe"] = self.last_parse_stats.get("dedupe", 0) + 1
            if max_id:
                self.media_store.advance_cursor(channel, max_id)
            return None

        listing = extract_car_data(
            raw_text=text,
            channel=channel,
            message_id=primary.id,
            group_message_ids=ids,
            source_link=await self._build_source_link(channel, primary.id),
            posted_at=primary.date,
            photos=[],
        )

        if not is_valid_car_listing(listing):
            if not self.skip_dedupe:
                self.dedupe.mark_seen(channel, ids)
            if max_id:
                self.media_store.advance_cursor(channel, max_id)
            self.last_parse_stats["invalid"] = self.last_parse_stats.get("invalid", 0) + 1
            return None

        # Lazy photos: без download на парсі — лише refs для worker/API
        listing.photos = []
        safe_channel = channel.lstrip("@").replace("/", "_").replace(" ", "_")
        self.media_store.save_photo_refs(
            f"telegram_{safe_channel}_{primary.id}",
            channel,
            ids,
        )
        if not self.skip_dedupe:
            self.dedupe.mark_seen(channel, ids)
        if max_id:
            self.media_store.advance_cursor(channel, max_id)
        self.last_parse_stats["valid"] = self.last_parse_stats.get("valid", 0) + 1
        return listing

    async def download_listing_photos(self, listing_id: str, channel: str, message_ids: list[int]) -> list[str]:
        """Завантажує ≤ TELEGRAM_MAX_PHOTOS для listing (викликає worker)."""
        return await download_photos_by_ids(self.client, channel, message_ids)

    async def parse_channel_history(self, channel: str, limit: int = 200) -> list:
        """
        Інкрементальний скан: лише повідомлення новіші за cursor каналу.
        Перший запуск (cursor=0) — останні `limit` повідомлень.
        """
        joined = await self._ensure_joined_cached(channel)
        if not joined:
            log.warning("Пропускаю %s - не вдалось приєднатись/отримати доступ", channel)
            return []

        entity = await self.client.get_entity(channel)
        if getattr(entity, "username", None):
            self._slug_cache[channel.strip()] = entity.username

        normalized = await self._normalize_channel(channel)
        cursor = 0 if self.skip_dedupe else self.media_store.get_cursor(normalized)
        raw_messages = []
        # min_id=cursor → лише id > cursor (після першого bootstrap)
        async for msg in self.client.iter_messages(entity, limit=limit, min_id=cursor):
            raw_messages.append(msg)

        self.last_parse_stats = {
            "messages": len(raw_messages),
            "groups": 0,
            "dedupe": 0,
            "empty": 0,
            "invalid": 0,
            "valid": 0,
            "cursor_from": cursor,
        }

        groups: dict = {}
        singles: list = []
        for m in raw_messages:
            if m.grouped_id:
                groups.setdefault(m.grouped_id, []).append(m)
            else:
                singles.append([m])

        all_groups = list(groups.values()) + singles
        self.last_parse_stats["groups"] = len(all_groups)

        results = []
        for group in all_groups:
            listing = await self._process_group(channel, group)
            if listing:
                results.append(listing)

        if raw_messages:
            batch_max = max(m.id for m in raw_messages)
            self.media_store.advance_cursor(normalized, batch_max)
            self.last_parse_stats["cursor_to"] = self.media_store.get_cursor(normalized)

        results.sort(key=lambda l: l.posted_at or datetime.min, reverse=True)
        log.info(
            "History %s: msgs=%s valid=%s cursor %s→%s",
            normalized,
            len(raw_messages),
            self.last_parse_stats.get("valid", 0),
            cursor,
            self.last_parse_stats.get("cursor_to", cursor),
        )
        return results

    async def listen(
        self,
        channels: list,
        on_new_listing: Callable[[CarListing], Awaitable[None]],
    ):
        """
        Постійно слухає нові повідомлення у вказаних каналах і викликає
        on_new_listing(listing) для кожного розпарсеного оголошення.
        Запускається "назавжди" - тримай у фоновій задачі/окремому процесі.
        """
        for ch in channels:
            await self._ensure_joined_cached(ch)
        entities = [await self.client.get_entity(ch) for ch in channels]
        channel_by_peer_id: dict[int, str] = {}
        for ch, entity in zip(channels, entities):
            label = f"@{entity.username}" if getattr(entity, "username", None) else ch
            channel_by_peer_id[get_peer_id(entity)] = label
            if getattr(entity, "username", None):
                self._slug_cache[ch.strip()] = entity.username
                self._slug_cache[label] = entity.username

        def _channel_from_event(chat_id: int) -> str:
            return channel_by_peer_id.get(chat_id, str(chat_id))

        @self.client.on(events.Album(chats=entities))
        async def _album_handler(event):
            channel = _channel_from_event(event.chat_id)
            listing = await self._process_group(channel, event.messages)
            if listing:
                await on_new_listing(listing)

        @self.client.on(events.NewMessage(chats=entities))
        async def _single_handler(event: events.NewMessage.Event):
            if event.message.grouped_id:
                return  # альбоми обробляються окремим хендлером вище
            channel = _channel_from_event(event.chat_id)
            listing = await self._process_group(channel, [event.message])
            if listing:
                await on_new_listing(listing)

        log.info("Слухаю нові оголошення в каналах: %s", channels)
        await self.client.run_until_disconnected()