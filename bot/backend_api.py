import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def link_telegram_account(
    token: str,
    telegram_id: str,
    telegram_username: str | None,
    chat_id: str,
) -> dict | None:
    url = f"{settings.BACKEND_URL}/internal/bot/connect"
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}
    payload = {
        "token": token,
        "telegram_id": telegram_id,
        "telegram_username": telegram_username,
        "chat_id": chat_id,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(url, json=payload, headers=headers)
        if res.status_code >= 400:
            logger.error("Backend connect failed: %s", res.text)
            return None
        return res.json()


async def init_telegram_login(
    telegram_id: str,
    telegram_username: str | None,
    chat_id: str,
) -> dict | None:
    url = f"{settings.BACKEND_URL}/internal/bot/login"
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}
    payload = {
        "telegram_id": telegram_id,
        "telegram_username": telegram_username,
        "chat_id": chat_id,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(url, json=payload, headers=headers)
        if res.status_code >= 400:
            logger.error("Backend login init failed: %s", res.text)
            return None
        return res.json()
