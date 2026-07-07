from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.timezone import KYIV_TZ, as_kyiv, now_kyiv

TIME_FIELD_KEYS = (
    "createdTime",
    "created_time",
    "lastRefreshTime",
    "last_refresh_time",
    "createdAt",
    "created_at",
    "pushupTime",
    "refreshTime",
)

UK_MONTHS = {
    "січня": 1,
    "січень": 1,
    "лютого": 2,
    "лютий": 2,
    "березня": 3,
    "березень": 3,
    "квітня": 4,
    "квітень": 4,
    "травня": 5,
    "травень": 5,
    "червня": 6,
    "червень": 6,
    "липня": 7,
    "липень": 7,
    "серпня": 8,
    "серпень": 8,
    "вересня": 9,
    "вересень": 9,
    "жовтня": 10,
    "жовтень": 10,
    "листопада": 11,
    "листопад": 11,
    "грудня": 12,
    "грудень": 12,
}


def _parse_iso_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1_000_000_000_000:
            ts /= 1000
        return as_kyiv(datetime.fromtimestamp(ts, tz=UTC))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return as_kyiv(datetime.fromisoformat(text.replace("Z", "+00:00")))
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
            try:
                return datetime.strptime(text, fmt).replace(tzinfo=KYIV_TZ)
            except ValueError:
                continue
    return None


def _extract_timestamp_from_raw(raw: dict | None) -> datetime | None:
    if not raw:
        return None

    def walk(node: Any) -> datetime | None:
        if isinstance(node, dict):
            for key in TIME_FIELD_KEYS:
                if key in node:
                    parsed = _parse_iso_datetime(node[key])
                    if parsed:
                        return parsed
            for value in node.values():
                parsed = walk(value)
                if parsed:
                    return parsed
        elif isinstance(node, list):
            for item in node:
                parsed = walk(item)
                if parsed:
                    return parsed
        return None

    return walk(raw)


def parse_olx_published_text(text: str, *, now: datetime | None = None) -> datetime | None:
    """
    Парсить текст з OLX (картка/деталі): «5 хвилин тому», «сьогодні о 14:30», «3 липня» тощо.
    """
    if not text:
        return None

    current = now or now_kyiv()
    normalized = " ".join(text.strip().lower().split())

    if normalized in {"щойно", "just now"}:
        return current

    relative_minutes = re.match(
        r"^(\d+)\s*(хв|хвилин|хвилини|хвилину|min|mins|minutes?)\s*тому$",
        normalized,
    )
    if relative_minutes:
        return current - timedelta(minutes=int(relative_minutes.group(1)))

    relative_hours = re.match(
        r"^(\d+)\s*(год|годин|години|годину|hr|hrs|hours?)\s*тому$",
        normalized,
    )
    if relative_hours:
        return current - timedelta(hours=int(relative_hours.group(1)))

    relative_days = re.match(
        r"^(\d+)\s*(дн|дні|днів|день|day|days?)\s*тому$",
        normalized,
    )
    if relative_days:
        return current - timedelta(days=int(relative_days.group(1)))

    relative_weeks = re.match(
        r"^(\d+)\s*(тиж|тижн|тижні|тижнів|тиждень|week|weeks?)\s*тому$",
        normalized,
    )
    if relative_weeks:
        return current - timedelta(weeks=int(relative_weeks.group(1)))

    time_match = re.search(r"о\s*(\d{1,2}):(\d{2})", normalized)

    if normalized.startswith("сьогодні") or normalized.startswith("today"):
        if time_match:
            return current.replace(
                hour=int(time_match.group(1)),
                minute=int(time_match.group(2)),
                second=0,
                microsecond=0,
            )
        return current.replace(hour=0, minute=0, second=0, microsecond=0)

    if normalized.startswith("вчора") or normalized.startswith("yesterday"):
        base = current - timedelta(days=1)
        if time_match:
            return base.replace(
                hour=int(time_match.group(1)),
                minute=int(time_match.group(2)),
                second=0,
                microsecond=0,
            )
        return base.replace(hour=0, minute=0, second=0, microsecond=0)

    dotted = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+о\s*(\d{1,2}):(\d{2}))?$", normalized)
    if dotted:
        hour = int(dotted.group(4) or 12)
        minute = int(dotted.group(5) or 0)
        return datetime(
            int(dotted.group(3)),
            int(dotted.group(2)),
            int(dotted.group(1)),
            hour,
            minute,
            tzinfo=KYIV_TZ,
        )

    month_match = re.match(
        r"^(\d{1,2})\s+([а-яіїєґ]+)(?:\s+(\d{4}))?(?:\s+о\s*(\d{1,2}):(\d{2}))?$",
        normalized,
    )
    if month_match:
        month = UK_MONTHS.get(month_match.group(2))
        if month:
            year = int(month_match.group(3) or current.year)
            hour = int(month_match.group(4) or 12)
            minute = int(month_match.group(5) or 0)
            return datetime(
                year,
                month,
                int(month_match.group(1)),
                hour,
                minute,
                tzinfo=KYIV_TZ,
            )

    return None


def resolve_olx_published_at(
    *,
    published: str | None,
    raw_params: dict | None = None,
    now: datetime | None = None,
) -> datetime:
    """Повертає дату публікації на OLX або now_kyiv() як останній fallback."""
    current = now or now_kyiv()

    from_raw = _extract_timestamp_from_raw(raw_params)
    if from_raw:
        return from_raw

    if published:
        from_iso = _parse_iso_datetime(published)
        if from_iso:
            return from_iso

        from_text = parse_olx_published_text(published, now=current)
        if from_text:
            return from_text

        # «Київ - 5 хвилин тому» — беремо частину після « - »
        if " - " in published:
            _, tail = published.split(" - ", 1)
            from_tail = parse_olx_published_text(tail.strip(), now=current)
            if from_tail:
                return from_tail
            from_tail_iso = _parse_iso_datetime(tail.strip())
            if from_tail_iso:
                return from_tail_iso

    return current
