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
