"""Сумісний фасад: чистка переїхала в app.services.listings.retention.

Строк зберігання тепер стосується всіх джерел, а не лише Telegram.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.listings.retention import purge_stale_listings


async def purge_stale_telegram_listings(db: AsyncSession) -> int:
    return await purge_stale_listings(db)
