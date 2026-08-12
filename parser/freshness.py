"""Вікно свіжості Telegram-оголошень."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .config import settings

# Не скануємо і не показуємо пости старші за LISTING_MAX_AGE_DAYS (типово 4 місяці).
TELEGRAM_LISTING_MAX_AGE_DAYS = settings.listing_max_age_days


def telegram_scan_cutoff_utc() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=settings.listing_max_age_days)


def message_date_is_fresh(msg_date: datetime | None, *, cutoff: datetime | None = None) -> bool:
    """True якщо дата повідомлення в межах вікна сканування."""
    if msg_date is None:
        return False
    limit = cutoff or telegram_scan_cutoff_utc()
    dt = msg_date
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt >= limit
