"""Свіжість Telegram-лістингів у пошуку (≤ 3 місяці)."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.timezone import as_kyiv, now_kyiv

TELEGRAM_LISTING_MAX_AGE_DAYS = 90


def telegram_published_cutoff() -> datetime:
    return now_kyiv() - timedelta(days=TELEGRAM_LISTING_MAX_AGE_DAYS)


def telegram_listing_is_fresh(
    published_at: datetime | None,
    *,
    found_at: datetime | None = None,
) -> bool:
    """True якщо оголошення не старше TELEGRAM_LISTING_MAX_AGE_DAYS.

    Без published_at не блокуємо (SQL/скан уже ріжуть за датою поста).
    found_at не використовується — важлива дата публікації в Telegram.
    """
    del found_at  # API-сумісність; свіжість = дата поста, не індексації
    if published_at is None:
        return True
    try:
        return as_kyiv(published_at) >= telegram_published_cutoff()
    except Exception:
        return True
