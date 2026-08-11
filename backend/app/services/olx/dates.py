from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.timezone import KYIV_TZ, as_kyiv, now_kyiv

# published_at: перша публікація
CREATED_TIME_KEYS = (
    "createdTime",
    "created_time",
    "createdAt",
    "created_at",
)
# refreshed_at: підняття / оновлення на OLX
REFRESH_TIME_KEYS = (
    "lastRefreshTime",
    "last_refresh_time",
    "pushupTime",
    "refreshTime",
)
# Сумісність: будь-який timestamp (спочатку created, потім refresh)
TIME_FIELD_KEYS = CREATED_TIME_KEYS + REFRESH_TIME_KEYS

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


def _extract_timestamp_from_raw(
    raw: dict | None,
    *,
    keys: tuple[str, ...] = TIME_FIELD_KEYS,
) -> datetime | None:
    if not raw:
        return None

    # Спочатку топ-рівень (оголошення), без глибокого walk — менше шансів
    # схопити чужий timestamp з вкладених об'єктів.
    for key in keys:
        if key in raw:
            parsed = _parse_iso_datetime(raw[key])
            if parsed:
                return parsed

    def walk(node: Any, *, depth: int = 0) -> datetime | None:
        if depth > 4:
            return None
        if isinstance(node, dict):
            for key in keys:
                if key in node:
                    parsed = _parse_iso_datetime(node[key])
                    if parsed:
                        return parsed
            for value in node.values():
                parsed = walk(value, depth=depth + 1)
                if parsed:
                    return parsed
        elif isinstance(node, list):
            for item in node:
                parsed = walk(item, depth=depth + 1)
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
    # «10 липня 2026 р.» / «10 липня 2026р.»
    normalized = re.sub(r"\s*р\.?\s*$", "", normalized)
    # «Опубліковано 10 липня» або злите «Опублікованосьогодні о 08:21» (get_text(strip=True))
    normalized = re.sub(r"^опубліковано\s*", "", normalized)
    # «Оновлено 4 год тому» — окремий рядок без «Опубліковано»
    normalized = re.sub(r"^оновлено\s*", "", normalized)

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


def split_olx_updated_published_text(text: str | None) -> tuple[str | None, str | None]:
    """
    Розбиває рядок OLX на частини «Оновлено …» та «Опубліковано …».
    Приклад: «Оновлено 4 год тому • Опубліковано 4 тиж тому».
    """
    if not text:
        return None, None

    normalized = " ".join(text.strip().split())
    parts = [part.strip() for part in re.split(r"\s*[•·]\s*", normalized) if part.strip()]
    updated_part: str | None = None
    published_part: str | None = None

    for part in parts:
        lower = part.lower()
        if lower.startswith("оновлено"):
            updated_part = re.sub(r"^оновлено\s*", "", part, count=1, flags=re.IGNORECASE).strip() or part
        elif lower.startswith("опубліковано"):
            published_part = re.sub(r"^опубліковано\s*", "", part, count=1, flags=re.IGNORECASE).strip() or part

    if len(parts) == 1 and not updated_part and not published_part:
        lower = normalized.lower()
        if lower.startswith("оновлено"):
            updated_part = re.sub(r"^оновлено\s*", "", normalized, count=1, flags=re.IGNORECASE).strip()
        elif lower.startswith("опубліковано"):
            published_part = re.sub(r"^опубліковано\s*", "", normalized, count=1, flags=re.IGNORECASE).strip()

    return updated_part, published_part


def resolve_olx_published_at(
    *,
    published: str | None,
    raw_params: dict | None = None,
    now: datetime | None = None,
) -> datetime:
    """Дата першої публікації (createdTime), не lastRefreshTime."""
    current = now or now_kyiv()

    from_created = _extract_timestamp_from_raw(raw_params, keys=CREATED_TIME_KEYS)
    if from_created:
        return from_created

    # Fallback: текст «Опубліковано…» / хвостик локації. Не плутаємо з lastRefresh.
    if published:
        updated_text, published_text = split_olx_updated_published_text(published)
        published_for_parse = published_text or (published if not updated_text else None) or published

        from_iso = _parse_iso_datetime(published_for_parse)
        refresh_from_raw = _extract_timestamp_from_raw(raw_params, keys=REFRESH_TIME_KEYS)
        iso_looks_like_refresh = bool(
            from_iso
            and refresh_from_raw
            and abs((from_iso - refresh_from_raw).total_seconds()) < 60
        )

        if from_iso and not iso_looks_like_refresh:
            return from_iso

        from_text = parse_olx_published_text(published_for_parse, now=current)
        if from_text:
            return from_text

        # «Київ - 5 хвилин тому» / «Київ – сьогодні о 08:21»
        for sep in (" - ", " – ", " — ", " • ", " · "):
            if sep in published_for_parse:
                _, tail = published_for_parse.split(sep, 1)
                from_tail = parse_olx_published_text(tail.strip(), now=current)
                if from_tail:
                    return from_tail
                from_tail_iso = _parse_iso_datetime(tail.strip())
                if from_tail_iso:
                    return from_tail_iso
                break

        if from_iso:
            return from_iso

    # Не підставляємо lastRefreshTime як дату публікації — це «підняття».
    return current


def resolve_olx_refreshed_at(
    *,
    published: str | None = None,
    raw_params: dict | None = None,
    published_at: datetime | None = None,
    now: datetime | None = None,
) -> datetime | None:
    """Дата оновлення/підняття (lastRefreshTime). None, якщо збігається з публікацією."""
    refreshed = _extract_timestamp_from_raw(raw_params, keys=REFRESH_TIME_KEYS)
    if refreshed is None and published:
        updated_text, published_text = split_olx_updated_published_text(published)
        if updated_text:
            refreshed = parse_olx_published_text(updated_text, now=now or now_kyiv())
        elif published_text is None:
            # Картки часто показують саме refresh у рядку «Сьогодні о …»
            text_dt = parse_olx_published_text(published, now=now or now_kyiv())
            if text_dt and published_at and abs((text_dt - published_at).total_seconds()) > 120:
                refreshed = text_dt
            elif text_dt and published_at is None:
                refreshed = text_dt

    if refreshed is None:
        return None
    if published_at and abs((refreshed - published_at).total_seconds()) < 60:
        return None
    return refreshed
