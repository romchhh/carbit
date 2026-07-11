from __future__ import annotations

from datetime import datetime

from app.core.timezone import as_kyiv, now_kyiv
from app.services.auto_ria.constants import (
    AUTO_RIA_TOP_12H,
    AUTO_RIA_TOP_24H,
    AUTO_RIA_TOP_3H,
    AUTO_RIA_TOP_6H,
    AUTO_RIA_TOP_HOUR,
    AUTO_RIA_TOP_TODAY,
)

# Допускаємо невелику різницю годинників джерела
_MAX_FUTURE_SKEW_SECONDS = 300
DEFAULT_NOTIFICATION_MAX_HOURS = 1.0


def coerce_notification_max_hours(value: object, default: float = DEFAULT_NOTIFICATION_MAX_HOURS) -> float:
    try:
        hours = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if hours <= 0:
        return default
    return min(hours, 24.0)


def auto_ria_top_for_max_hours(max_hours: float | int | None) -> int | None:
    """Підбирає параметр top для AUTO.RIA search за вікном свіжості."""
    if not max_hours:
        return None
    hours = float(max_hours)
    if hours <= 1:
        return AUTO_RIA_TOP_HOUR
    if hours <= 3:
        return AUTO_RIA_TOP_3H
    if hours <= 6:
        return AUTO_RIA_TOP_6H
    if hours <= 12:
        return AUTO_RIA_TOP_12H
    if hours <= 24:
        return AUTO_RIA_TOP_24H
    return AUTO_RIA_TOP_TODAY


def is_listing_fresh_for_notification(
    published_at: datetime | None,
    *,
    max_hours: float,
    now: datetime | None = None,
) -> bool:
    """Чи достатньо свіже оголошення для Telegram-сповіщення."""
    if published_at is None or max_hours <= 0:
        return False

    current = now or now_kyiv()
    published = as_kyiv(published_at)
    age_seconds = (current - published).total_seconds()

    if age_seconds < -_MAX_FUTURE_SKEW_SECONDS:
        return False
    if age_seconds < 0:
        return True

    return age_seconds <= float(max_hours) * 3600
