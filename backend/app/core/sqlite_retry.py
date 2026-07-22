"""Retry flush/commit when SQLite is contended (parser + admin deliver)."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


def _sqlite_locked(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        msg = str(current).lower()
        if "database is locked" in msg or "database locked" in msg:
            return True
        current = current.__cause__ or getattr(current, "orig", None)
    return False


async def flush_session(
    db: AsyncSession,
    *,
    attempts: int = 24,
    base_delay: float = 0.2,
) -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        await db.flush()
        return
    last: OperationalError | None = None
    for attempt in range(attempts):
        try:
            await db.flush()
            return
        except OperationalError as exc:
            if not _sqlite_locked(exc):
                raise
            last = exc
            delay = min(base_delay * (attempt + 1), 2.5)
            logger.warning(
                "SQLite locked on flush, retry %s/%s in %.1fs",
                attempt + 1,
                attempts,
                delay,
            )
            await asyncio.sleep(delay)
    assert last is not None
    raise last


async def commit_session(
    db: AsyncSession,
    *,
    attempts: int = 24,
    base_delay: float = 0.2,
) -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        await db.commit()
        return
    last: OperationalError | None = None
    for attempt in range(attempts):
        try:
            await db.commit()
            return
        except OperationalError as exc:
            if not _sqlite_locked(exc):
                raise
            last = exc
            delay = min(base_delay * (attempt + 1), 2.5)
            logger.warning(
                "SQLite locked on commit, retry %s/%s in %.1fs",
                attempt + 1,
                attempts,
                delay,
            )
            await asyncio.sleep(delay)
    assert last is not None
    raise last
