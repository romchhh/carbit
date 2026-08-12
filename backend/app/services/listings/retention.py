"""Строк зберігання оголошень: старі видаляються з БД разом із фото."""

from __future__ import annotations

import logging

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing
from app.services.telegram_channels.freshness import (
    listing_max_age_days,
    telegram_published_cutoff,
)
from app.services.telegram_channels.media_cleanup import (
    delete_media_for_listing_ids,
    delete_orphan_photo_refs,
    purge_stale_media_files,
)

logger = logging.getLogger(__name__)

# Скільки видаляємо за один прохід: щоб не тримати довгу транзакцію.
PURGE_BATCH_LIMIT = 2000


def _stale_condition(cutoff):
    """Старе за датою публікації; якщо її немає — за датою знахідки."""
    return or_(
        Listing.published_at < cutoff,
        and_(Listing.published_at.is_(None), Listing.found_at < cutoff),
    )


async def _clean_orphan_photo_refs(db: AsyncSession) -> None:
    """Фото повідомлень, які ingest відсіяв, теж мають зникати."""
    try:
        live_ids = set(
            (
                await db.scalars(
                    select(Listing.id).where(Listing.id.like("telegram_%"))
                )
            ).all()
        )
        delete_orphan_photo_refs(live_ids)
    except Exception:
        logger.debug("Orphan photo refs cleanup failed", exc_info=True)


async def count_stale_listings(db: AsyncSession) -> int:
    cutoff = telegram_published_cutoff()
    return int(
        await db.scalar(
            select(func.count()).select_from(Listing).where(_stale_condition(cutoff))
        )
        or 0
    )


async def purge_stale_listings(db: AsyncSession, *, limit: int = PURGE_BATCH_LIMIT) -> int:
    """Видаляє оголошення старші за строк зберігання — усі джерела, з фото.

    Telegram чистився й раніше, а OLX / AUTO.RIA накопичувались без обмежень.
    """
    cutoff = telegram_published_cutoff()
    stale_ids = list(
        (
            await db.scalars(
                select(Listing.id).where(_stale_condition(cutoff)).limit(max(1, limit))
            )
        ).all()
    )
    if not stale_ids:
        await _clean_orphan_photo_refs(db)
        return 0

    # Локальні файли має лише Telegram; в інших джерел images — зовнішні URL.
    telegram_ids = [lid for lid in stale_ids if lid.startswith("telegram_")]
    if telegram_ids:
        delete_media_for_listing_ids(telegram_ids)

    # duplicate_of без ON DELETE — спочатку відв'язуємо посилання.
    await db.execute(
        update(Listing).where(Listing.duplicate_of.in_(stale_ids)).values(duplicate_of=None)
    )
    await db.execute(delete(Listing).where(Listing.id.in_(stale_ids)))
    purge_stale_media_files()
    await _clean_orphan_photo_refs(db)
    logger.info(
        "Purged %s listings older than %s days (cutoff=%s, telegram=%s)",
        len(stale_ids),
        listing_max_age_days(),
        cutoff.isoformat(),
        len(telegram_ids),
    )
    return len(stale_ids)
