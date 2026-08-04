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
from .freshness import message_date_is_fresh, telegram_scan_cutoff_utc
from .media import download_photos_by_ids
from .dedupe import DedupeStore
from .channel_media_store import ChannelMediaStore
from .models import CarListing

log = logging.getLogger("carbit_parser.service")
logging.basicConfig(level=logging.INFO)


async def _record_telegram_channels(operation: str, *, success: bool = True) -> None:
    try:
        from app.services.admin.api_usage import record_api_request

        await record_api_request("telegram_channels", operation, success=success)
    except Exception:
        pass


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
        self._listen_handlers_registered = False
        self._peer_to_channel: dict[int, str] = {}
        self._on_new_listing: Callable[[CarListing], Awaitable[None]] | None = None

    @staticmethod
    def _message_is_fresh(msg, *, cutoff: datetime | None = None) -> bool:
        return message_date_is_fresh(getattr(msg, "date", None), cutoff=cutoff)

    async def start(self):
        for name in ("telethon", "telethon.network", "telethon.client"):
            logging.getLogger(name).setLevel(logging.WARNING)
        await self.client.start(phone=settings.phone or None)
        log.info("Telethon клієнт запущено")

    async def stop(self):
        await self.client.disconnect()

    async def _telethon_ref(self, channel: str) -> str:
        ch = (channel or "").strip()
        if ch.startswith("@+"):
            return f"https://t.me/{ch[1:]}"
        return ch

    async def _ensure_joined_cached(self, channel: str) -> bool:
        if channel in self._joined_cache:
            return True
        ok = await ensure_joined(self.client, await self._telethon_ref(channel))
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

    async def _process_group(
        self,
        channel: str,
        group_messages: list,
        *,
        touch_cursor: bool = True,
        force_reparse: bool = False,
    ) -> Optional[CarListing]:
        """group_messages - список Message з однаковим grouped_id (або 1 повідомлення).

        Фото НЕ качаємо тут (lazy): лише валідуємо текст і зберігаємо refs.
        touch_cursor=False — для keyword-пошуку по історії (не зсуваємо інкрементальний cursor).
        force_reparse=True — ігнорує seen_messages (keyword/history мають виправити wrong brand).
        """
        channel = await self._normalize_channel(channel)
        group_messages = sorted(group_messages, key=lambda m: m.id)
        primary = next((m for m in group_messages if (m.text or "").strip()), group_messages[0])
        text = self._merge_group_text(group_messages)
        ids = [m.id for m in group_messages]
        max_id = max(ids) if ids else 0

        if not text.strip() and not any(m.photo for m in group_messages):
            self.last_parse_stats["empty"] = self.last_parse_stats.get("empty", 0) + 1
            if touch_cursor and max_id:
                self.media_store.advance_cursor(channel, max_id)
            return None

        if not force_reparse and not self.skip_dedupe and self.dedupe.is_seen(channel, primary.id):
            self.last_parse_stats["dedupe"] = self.last_parse_stats.get("dedupe", 0) + 1
            if touch_cursor and max_id:
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

        # Не індексуємо пости старші за 3 місяці (навіть якщо проскочили в iter).
        if listing.posted_at and not message_date_is_fresh(listing.posted_at):
            if not self.skip_dedupe:
                self.dedupe.mark_seen(channel, ids)
            if touch_cursor and max_id:
                self.media_store.advance_cursor(channel, max_id)
            self.last_parse_stats["invalid"] = self.last_parse_stats.get("invalid", 0) + 1
            return None

        if not is_valid_car_listing(listing):
            if not self.skip_dedupe:
                self.dedupe.mark_seen(channel, ids)
            if touch_cursor and max_id:
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
        if touch_cursor and max_id:
            self.media_store.advance_cursor(channel, max_id)
        self.last_parse_stats["valid"] = self.last_parse_stats.get("valid", 0) + 1
        return listing

    async def download_listing_photos(
        self,
        listing_id: str,
        channel: str,
        message_ids: list[int],
        *,
        max_photos: int | None = None,
    ) -> list[str]:
        """Завантажує ≤ max_photos (або TELEGRAM_MAX_PHOTOS) для listing."""
        return await download_photos_by_ids(
            self.client,
            channel,
            message_ids,
            max_photos=max_photos,
        )

    async def parse_channel_history(self, channel: str, limit: int = 200) -> list:
        """
        Інкрементальний скан: лише повідомлення новіші за cursor каналу.
        Перший запуск (cursor=0) — останні `limit` повідомлень.
        """
        joined = await self._ensure_joined_cached(channel)
        if not joined:
            log.warning("Пропускаю %s - не вдалось приєднатись/отримати доступ", channel)
            return []

        entity = await self.client.get_entity(await self._telethon_ref(channel))
        if getattr(entity, "username", None):
            self._slug_cache[channel.strip()] = entity.username

        normalized = await self._normalize_channel(channel)
        cursor = 0 if self.skip_dedupe else self.media_store.get_cursor(normalized)
        raw_messages = []
        cutoff = telegram_scan_cutoff_utc()
        # min_id=cursor → лише id > cursor (після першого bootstrap)
        async for msg in self.client.iter_messages(entity, limit=limit, min_id=cursor):
            if not self._message_is_fresh(msg, cutoff=cutoff):
                break  # newest → oldest
            raw_messages.append(msg)

        await _record_telegram_channels("history")

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

    async def scan_channel_history_for_filters(
        self,
        channel: str,
        *,
        brand: str,
        model: str = "",
        limit: int = 500,
    ) -> list:
        """Повний scan історії каналу; матчинг за усіма brand/model keyword-варіантами."""
        brand = (brand or "").strip()
        model = (model or "").strip()
        if not brand and not model:
            return []

        from app.services.search.brand_model_keywords import message_matches_search_filters

        joined = await self._ensure_joined_cached(channel)
        if not joined:
            log.warning("History scan: пропускаю %s — немає доступу", channel)
            return []

        entity = await self.client.get_entity(await self._telethon_ref(channel))
        if getattr(entity, "username", None):
            self._slug_cache[channel.strip()] = entity.username

        normalized = await self._normalize_channel(channel)
        raw_messages: list = []
        cutoff = telegram_scan_cutoff_utc()
        async for msg in self.client.iter_messages(entity, limit=max(10, int(limit))):
            if not self._message_is_fresh(msg, cutoff=cutoff):
                break  # newest → oldest: далі тільки старіше за 3 міс.
            raw_messages.append(msg)

        await _record_telegram_channels("history_scan")

        self.last_parse_stats = {
            "messages": len(raw_messages),
            "groups": 0,
            "dedupe": 0,
            "empty": 0,
            "invalid": 0,
            "valid": 0,
            "brand": brand,
            "model": model,
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
            text = self._merge_group_text(group)
            if not message_matches_search_filters(text, brand, model):
                continue
            listing = await self._process_group(
                channel, group, touch_cursor=False, force_reparse=True
            )
            if listing:
                results.append(listing)

        results.sort(key=lambda l: l.posted_at or datetime.min, reverse=True)
        log.info(
            "History scan %s brand=%r model=%r: msgs=%s matched=%s",
            normalized,
            brand,
            model,
            len(raw_messages),
            len(results),
        )
        return results

    async def search_channel_by_keywords(
        self,
        channel: str,
        query: str,
        *,
        limit: int = 50,
        brand: str = "",
        model: str = "",
    ) -> list:
        """Пошук по історії каналу за ключовими словами (Telethon search).

        Не чіпає інкрементальний cursor — лише підтягує релевантні пости в індекс.
        Якщо задано brand/model — пост-фільтр message_matches_search_filters.
        """
        query = (query or "").strip()
        if not query:
            return []

        brand = (brand or "").strip()
        model = (model or "").strip()
        use_post_filter = bool(brand or model)
        if use_post_filter:
            from app.services.search.brand_model_keywords import message_matches_search_filters

        joined = await self._ensure_joined_cached(channel)
        if not joined:
            log.warning("Keyword search: пропускаю %s — немає доступу", channel)
            return []

        entity = await self.client.get_entity(await self._telethon_ref(channel))
        if getattr(entity, "username", None):
            self._slug_cache[channel.strip()] = entity.username

        normalized = await self._normalize_channel(channel)
        raw_messages = []
        cutoff = telegram_scan_cutoff_utc()
        async for msg in self.client.iter_messages(entity, search=query, limit=limit):
            # search не гарантує порядок за датою — лише пропускаємо старі.
            if not self._message_is_fresh(msg, cutoff=cutoff):
                continue
            raw_messages.append(msg)

        await _record_telegram_channels("keyword_search")

        self.last_parse_stats = {
            "messages": len(raw_messages),
            "groups": 0,
            "dedupe": 0,
            "empty": 0,
            "invalid": 0,
            "valid": 0,
            "query": query,
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
            if use_post_filter:
                text = self._merge_group_text(group)
                if not message_matches_search_filters(text, brand, model):
                    continue
            listing = await self._process_group(
                channel, group, touch_cursor=False, force_reparse=True
            )
            if listing:
                results.append(listing)

        results.sort(key=lambda l: l.posted_at or datetime.min, reverse=True)
        log.info(
            "Keyword search %s q=%r: msgs=%s valid=%s",
            normalized,
            query,
            len(raw_messages),
            self.last_parse_stats.get("valid", 0),
        )
        return results

    async def sync_monitored_channels(self, channels: list[str]) -> list[str]:
        """Приєднується до каналів і оновлює мапу peer_id → @username для listen()."""
        active: list[str] = []
        peer_map: dict[int, str] = {}
        for ch in channels:
            key = (ch or "").strip()
            if not key:
                continue
            joined = await self._ensure_joined_cached(key)
            if not joined:
                continue
            try:
                entity = await self.client.get_entity(await self._telethon_ref(key))
            except Exception as exc:
                log.warning("sync_monitored_channels: не знайдено %s: %s", key, exc)
                continue
            label = f"@{entity.username}" if getattr(entity, "username", None) else key
            peer_map[get_peer_id(entity)] = label
            if getattr(entity, "username", None):
                self._slug_cache[key] = entity.username
                self._slug_cache[label] = entity.username
            active.append(key)
        self._peer_to_channel = peer_map
        return active

    def _register_listen_handlers(self) -> None:
        if self._listen_handlers_registered:
            return
        self._listen_handlers_registered = True

        def _channel_from_event(chat_id: int) -> str | None:
            return self._peer_to_channel.get(chat_id)

        @self.client.on(events.Album())
        async def _album_handler(event):
            channel = _channel_from_event(event.chat_id)
            if not channel:
                return
            listing = await self._process_group(channel, event.messages)
            if listing and self._on_new_listing:
                await self._on_new_listing(listing)

        @self.client.on(events.NewMessage())
        async def _single_handler(event: events.NewMessage.Event):
            channel = _channel_from_event(event.chat_id)
            if not channel:
                return
            if event.message.grouped_id:
                return
            listing = await self._process_group(channel, [event.message])
            if listing and self._on_new_listing:
                await self._on_new_listing(listing)

    async def listen(
        self,
        channels: list,
        on_new_listing: Callable[[CarListing], Awaitable[None]],
    ):
        """
        Постійно слухає нові повідомлення у вказаних каналах.
        Список каналів можна оновлювати через sync_monitored_channels() (telegram_worker).
        """
        self._on_new_listing = on_new_listing
        active = await self.sync_monitored_channels(channels)
        self._register_listen_handlers()
        log.info("Слухаю нові оголошення в каналах: %s", active)
        await self.client.run_until_disconnected()