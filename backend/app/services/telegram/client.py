import html
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.core.timezone import as_kyiv, format_time_ago
from app.services.telegram.media_urls import (
    is_public_http_url,
    resolve_listing_image_url,
    telegram_media_local_path,
)

logger = logging.getLogger(__name__)

SOURCE_LABELS = {"auto_ria": "AUTO.RIA", "olx": "OLX", "telegram": "Telegram"}


def _published_caption_line(listing: dict) -> str | None:
    raw = listing.get("published_at")
    if not raw:
        return None
    if isinstance(raw, datetime):
        dt = raw
    else:
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            return None
    ago = format_time_ago(as_kyiv(dt))
    return f"🕐 Опубліковано {ago}" if ago else None


def _valid_photo_url(url: str | None) -> str | None:
    if not url or not isinstance(url, str):
        return None
    normalized = url.strip()
    if not is_public_http_url(normalized):
        return None
    lowered = normalized.lower()
    if "no_thumbnail" in lowered or "/app/static/" in lowered:
        return None
    return normalized


class TelegramClient:
    def __init__(self, token: str | None = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.base = f"https://api.telegram.org/bot{self.token}"

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    async def _call(self, method: str, payload: dict) -> dict | None:
        if not self.enabled:
            logger.warning("Telegram bot token not configured")
            return None
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(f"{self.base}/{method}", json=payload)
            if res.status_code >= 400:
                logger.error("Telegram API %s: %s", method, res.text)
                return None
            return res.json()

    async def _call_multipart(
        self,
        method: str,
        data: dict[str, Any],
        files: dict[str, tuple],
    ) -> dict | None:
        if not self.enabled:
            logger.warning("Telegram bot token not configured")
            return None
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(f"{self.base}/{method}", data=data, files=files)
            if res.status_code >= 400:
                logger.error("Telegram API %s (multipart): %s", method, res.text)
                return None
            return res.json()

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        reply_markup: dict | None = None,
        parse_mode: str = "HTML",
    ) -> dict | None:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self._call("sendMessage", payload)

    async def send_photo(
        self,
        chat_id: str | int,
        photo_url: str,
        caption: str,
        reply_markup: dict | None = None,
        parse_mode: str = "HTML",
    ) -> dict | None:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption[:1024],
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        result = await self._call("sendPhoto", payload)
        if result and result.get("ok"):
            return result
        return None

    async def send_photo_file(
        self,
        chat_id: str | int,
        file_path: Path,
        caption: str,
        reply_markup: dict | None = None,
        parse_mode: str = "HTML",
    ) -> dict | None:
        data: dict[str, Any] = {
            "chat_id": str(chat_id),
            "caption": caption[:1024],
            "parse_mode": parse_mode,
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)

        with file_path.open("rb") as handle:
            result = await self._call_multipart(
                "sendPhoto",
                data,
                {"photo": (file_path.name, handle, "image/jpeg")},
            )
        if result and result.get("ok"):
            return result
        return None

    async def send_listing_card(
        self,
        chat_id: str | int,
        listing: dict,
        search_name: str,
        *,
        search_id: str | None = None,
        listing_id: str | None = None,
        alert_line: str | None = None,
        alert_emoji: str = "📉",
    ) -> dict | None:
        source = listing.get("source", "")
        source_label = listing.get("source_label") or SOURCE_LABELS.get(source, source)
        if listing.get("display_price"):
            price_line = str(listing["display_price"])
        else:
            from app.services.currency import format_display_price

            price_line = format_display_price(
                listing.get("price"),
                listing.get("currency"),
                listing.get("preferred_currency") or "USD",
            )

        published_line = _published_caption_line(listing)
        title_emoji = alert_emoji if alert_line else "🚗"

        lines = [
            f"{title_emoji} <b>{html.escape(str(listing.get('title', 'Авто')))}</b>",
        ]
        if alert_line:
            lines.append(html.escape(alert_line))
        lines.extend([
            "",
            f"📅 {listing.get('year', '—')}  ·  🛣 {listing.get('mileage', 0):,} км".replace(",", " "),
            f"⛽ {html.escape(str(listing.get('fuel') or '—'))}  ·  ⚙️ {html.escape(str(listing.get('transmission') or '—'))}",
            f"📍 {html.escape(str(listing.get('region') or 'Україна'))}",
            f"💰 <b>{html.escape(price_line)}</b>",
            f"📡 {html.escape(source_label)}",
        ])
        if published_line:
            lines.append(published_line)
        lines.extend(["", f"🔍 <i>{html.escape(search_name)}</i>"])

        description = (listing.get("description") or "").strip()
        if description:
            short = description[:280] + ("…" if len(description) > 280 else "")
            lines.extend(["", html.escape(short)])

        caption = "\n".join(lines)

        app_listing_url = f"{settings.FRONTEND_URL.rstrip('/')}/app/listing/{listing_id}" if listing_id else listing.get("url")
        filters_url = (
            f"{settings.FRONTEND_URL.rstrip('/')}/app/results?search={search_id}"
            if search_id
            else f"{settings.FRONTEND_URL.rstrip('/')}/app/search"
        )

        markup = {
            "inline_keyboard": [
                [
                    {"text": "🌐 Переглянути", "url": app_listing_url or listing.get("url") or settings.FRONTEND_URL},
                ],
                [
                    {"text": "⚙️ Налаштувати фільтри", "url": filters_url},
                    {"text": "🔗 Джерело", "url": listing.get("url") or app_listing_url},
                ],
            ]
        }

        images = listing.get("images") or []
        raw_image = images[0] if images else listing.get("photo_url")
        local_path = telegram_media_local_path(str(raw_image) if raw_image else None)
        public_url = _valid_photo_url(resolve_listing_image_url(str(raw_image) if raw_image else None))

        if public_url:
            result = await self.send_photo(chat_id, public_url, caption, reply_markup=markup)
            if result:
                return result
            logger.warning("Telegram sendPhoto by URL failed, trying local file: %s", public_url)

        if local_path:
            result = await self.send_photo_file(chat_id, local_path, caption, reply_markup=markup)
            if result:
                return result
            logger.warning("Telegram sendPhoto by file failed: %s", local_path)

        return await self.send_message(chat_id, caption, reply_markup=markup)

    async def get_user_profile_photo_path(self, user_id: str | int) -> str | None:
        data = await self._call("getUserProfilePhotos", {"user_id": int(user_id), "limit": 1})
        if not data or not data.get("ok"):
            return None
        photos = data.get("result", {}).get("photos", [])
        if not photos:
            return None
        file_id = photos[0][-1]["file_id"]
        file_data = await self._call("getFile", {"file_id": file_id})
        if not file_data or not file_data.get("ok"):
            return None
        return file_data["result"]["file_path"]

    async def get_file_bytes(self, file_path: str) -> bytes | None:
        if not self.enabled:
            return None
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(url)
            if res.status_code >= 400:
                logger.error("Telegram file download failed: %s", res.text)
                return None
            return res.content


telegram_client = TelegramClient()
