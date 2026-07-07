from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

KYIV_TZ = ZoneInfo("Europe/Kyiv")


def now_kyiv() -> datetime:
    return datetime.now(KYIV_TZ)


def as_kyiv(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=KYIV_TZ)
    return dt.astimezone(KYIV_TZ)


def start_of_kyiv_day(dt: datetime | None = None) -> datetime:
    current = as_kyiv(dt) if dt else now_kyiv()
    return current.replace(hour=0, minute=0, second=0, microsecond=0)


def format_kyiv(dt: datetime | None = None, *, with_seconds: bool = True) -> str:
    current = as_kyiv(dt) if dt else now_kyiv()
    if with_seconds:
        return current.strftime("%d.%m.%Y, %H:%M:%S")
    return current.strftime("%d.%m.%Y")


def format_time_ago(dt: datetime | None) -> str | None:
    """Відносний час публікації: «5 хв тому», «1 год тому» тощо."""
    if dt is None:
        return None
    diff = (now_kyiv() - as_kyiv(dt)).total_seconds()
    if diff < 0:
        return None
    if diff < 60:
        return "щойно"
    mins = int(diff // 60)
    if mins < 60:
        return f"{mins} хв тому"
    hours = mins // 60
    if hours < 24:
        return f"{hours} год тому"
    days = hours // 24
    if days < 7:
        return f"{days} дн тому"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks} тиж тому"
    return format_kyiv(dt, with_seconds=False)
