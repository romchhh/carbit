"""Очищення застарілих Telegram-оголошень з БД."""

from __future__ import annotations

import logging

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, Source
from app.services.telegram_channels.freshness import (
    TELEGRAM_LISTING_MAX_AGE_DAYS,
    telegram_published_cutoff,
)

logger = logging.getLogger(__name__)


async def purge_stale_telegram_listings(db: AsyncSession) -> int:
    """Видаляє TG-оголошення старші за TELEGRAM_LISTING_MAX_AGE_DAYS.

    Критерій: published_at < cutoff; якщо published_at порожній — found_at < cutoff.
    """
    cutoff = telegram_published_cutoff()
    stale_ids = list(
        (
            await db.scalars(
                select(Listing.id).where(
                    Listing.source == Source.telegram,
                    or_(
                        Listing.published_at < cutoff,
                        and_(
                            Listing.published_at.is_(None),
                            Listing.found_at < cutoff,
                        ),
                    ),
                )
            )
        ).all()
    )
    if not stale_ids:
        return 0

    # duplicate_of без ON DELETE — спочатку відв'язуємо посилання.
    await db.execute(
        update(Listing)
        .where(Listing.duplicate_of.in_(stale_ids))
        .values(duplicate_of=None)
    )
    await db.execute(delete(Listing).where(Listing.id.in_(stale_ids)))
    logger.info(
        "Purged %s Telegram listings older than %s days (cutoff=%s)",
        len(stale_ids),
        TELEGRAM_LISTING_MAX_AGE_DAYS,
        cutoff.isoformat(),
    )
    return len(stale_ids)
