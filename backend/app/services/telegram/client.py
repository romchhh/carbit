import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


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

    async def send_listing_card(self, chat_id: str | int, listing: dict, search_name: str) -> dict | None:
        price = f"{listing['price']:,}".replace(",", " ")
        text = (
            f"🚗 <b>{listing['title']}</b>\n"
            f"📅 {listing['year']} · 🛣 {listing['mileage']:,} км · 📍 {listing['region']}\n"
            f"💰 <b>{price} {listing.get('currency', 'UAH')}</b>\n"
            f"🔍 Запит: «{search_name}»\n"
            f"📡 {listing.get('source_label', listing.get('source', ''))}"
        )
        markup = {
            "inline_keyboard": [[
                {"text": "Детальніше →", "url": listing.get("url") or settings.FRONTEND_URL},
            ]]
        }
        return await self.send_message(chat_id, text, reply_markup=markup)

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
