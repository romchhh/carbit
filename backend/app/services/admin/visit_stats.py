"""Облік відвідувань сайту (pageviews, geo, online) у Redis/KV для адмін-дашборду."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import Request

from app.core.redis import get_redis
from app.core.timezone import now_kyiv

logger = logging.getLogger(__name__)

HOUR_TTL_SECONDS = 60 * 60 * 24 * 35
DAY_TTL_SECONDS = 60 * 60 * 24 * 95
ONLINE_WINDOW_SECONDS = 300
ONLINE_KEY = "visit:online"
BOT_UA_RE = re.compile(
    r"bot|crawl|spider|slurp|facebookexternalhit|whatsapp|telegrambot|preview|headless",
    re.I,
)

COUNTRY_LABELS: dict[str, str] = {
    "UA": "Україна",
    "PL": "Польща",
    "DE": "Німеччина",
    "US": "США",
    "GB": "Велика Британія",
    "CZ": "Чехія",
    "SK": "Словаччина",
    "RO": "Румунія",
    "MD": "Молдова",
    "IT": "Італія",
    "FR": "Франція",
    "ES": "Іспанія",
    "NL": "Нідерланди",
    "CA": "Канада",
    "TR": "Туреччина",
    "LT": "Литва",
    "LV": "Латвія",
    "EE": "Естонія",
    "AT": "Австрія",
    "CH": "Швейцарія",
    "BE": "Бельгія",
    "HU": "Угорщина",
    "GE": "Грузія",
    "KZ": "Казахстан",
    "IL": "Ізраїль",
    "AE": "ОАЕ",
    "XX": "Невідомо",
}


def country_label(code: str | None) -> str:
    normalized = (code or "XX").strip().upper()[:2] or "XX"
    return COUNTRY_LABELS.get(normalized, normalized)


async def resolve_visit_country(request: Request) -> str:
    from app.services.admin.geo_ip import resolve_visit_country as _resolve

    return await _resolve(request)


def normalize_path(path: str | None) -> str:
    raw = (path or "/").strip()
    if not raw.startswith("/"):
        raw = f"/{raw}"
    raw = raw.split("?", 1)[0].split("#", 1)[0]
    if len(raw) > 1 and raw.endswith("/"):
        raw = raw.rstrip("/")
    if not raw:
        return "/"
    return raw[:180]


def path_label(path: str) -> str:
    labels = {
        "/": "Головна",
        "/pricing": "Тарифи",
        "/auth/login": "Вхід",
        "/app/search": "Пошук",
        "/app/monitors": "Моніторинг",
        "/app/compare": "Порівняння",
        "/app/account": "Кабінет",
        "/app/billing": "Оплата",
        "/app/vin": "Перевірка VIN",
        "/privacy": "Конфіденційність",
        "/terms": "Умови",
    }
    if path in labels:
        return labels[path]
    if path.startswith("/app/listing/"):
        return "Оголошення (шеринг)"
    if path.startswith("/legal/"):
        return "Юридичні сторінки"
    return path


def is_bot_user_agent(user_agent: str | None) -> bool:
    return bool(user_agent and BOT_UA_RE.search(user_agent))


def _hour_key(dt: datetime | None = None) -> str:
    ts = dt or now_kyiv()
    return f"visit:hour:{ts.strftime('%Y-%m-%d-%H')}"


def _day_key(dt: datetime | None = None) -> str:
    ts = dt or now_kyiv()
    return f"visit:day:{ts.strftime('%Y-%m-%d')}"


def _geo_day_key(dt: datetime | None = None) -> str:
    ts = dt or now_kyiv()
    return f"visit:geo:day:{ts.strftime('%Y-%m-%d')}"


def _paths_day_key(dt: datetime | None = None) -> str:
    ts = dt or now_kyiv()
    return f"visit:paths:day:{ts.strftime('%Y-%m-%d')}"


def _hour_of_day_key(dt: datetime | None = None) -> str:
    ts = dt or now_kyiv()
    return f"visit:hod:day:{ts.strftime('%Y-%m-%d')}"


def _seen_visitor_key(day: str, visitor_id: str) -> str:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", visitor_id)[:48] or "anon"
    return f"visit:seen:{day}:{safe_id}"


async def _touch_online(redis, visitor_id: str) -> None:
    now_ts = time.time()
    member = re.sub(r"[^a-zA-Z0-9_-]", "", visitor_id)[:48] or "anon"
    await redis.zadd(ONLINE_KEY, {member: now_ts})
    await redis.expire(ONLINE_KEY, ONLINE_WINDOW_SECONDS * 4)
    cutoff = now_ts - ONLINE_WINDOW_SECONDS
    await redis.zremrangebyscore(ONLINE_KEY, 0, cutoff)


async def record_visit(
    *,
    path: str,
    visitor_id: str,
    country: str = "XX",
    user_agent: str | None = None,
    device: str | None = None,
) -> None:
    if is_bot_user_agent(user_agent):
        return

    normalized_path = normalize_path(path)
    if normalized_path.startswith("/admin") or normalized_path.startswith("/api"):
        return

    country_code = (country or "XX").strip().upper()[:2] or "XX"
    visitor = (visitor_id or "").strip()[:64]
    if not visitor:
        return

    device_key = (device or "unknown").strip().lower()[:16] or "unknown"
    hour_slot = now_kyiv().hour

    try:
        redis = await get_redis()
        now = now_kyiv()
        day = now.strftime("%Y-%m-%d")
        hour_key = _hour_key(now)
        day_key = _day_key(now)
        geo_key = _geo_day_key(now)
        paths_key = _paths_day_key(now)
        hod_key = _hour_of_day_key(now)

        seen_key = _seen_visitor_key(day, visitor)
        is_new_today = not await redis.exists(seen_key)
        if is_new_today:
            await redis.setex(seen_key, DAY_TTL_SECONDS, "1")

        for key, ttl in (
            (hour_key, HOUR_TTL_SECONDS),
            (day_key, DAY_TTL_SECONDS),
            (geo_key, DAY_TTL_SECONDS),
            (paths_key, DAY_TTL_SECONDS),
            (hod_key, DAY_TTL_SECONDS),
        ):
            await redis.hincrby(key, "total", 1)
            await redis.expire(key, ttl)

        if is_new_today:
            await redis.hincrby(day_key, "unique", 1)

        await redis.hincrby(geo_key, country_code, 1)
        await redis.hincrby(paths_key, normalized_path, 1)
        await redis.hincrby(hod_key, str(hour_slot), 1)
        await redis.hincrby(day_key, f"device:{device_key}", 1)
        await _touch_online(redis, visitor)
    except Exception:
        logger.warning("visit_stats record failed path=%s", normalized_path, exc_info=True)


async def _read_int_field(key: str, field: str) -> int:
    redis = await get_redis()
    raw = await redis.hgetall(key)
    if not raw:
        return 0
    for k, value in raw.items():
        name = k.decode() if isinstance(k, bytes) else str(k)
        if name != field:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    return 0


async def _read_hash_ints(key: str) -> dict[str, int]:
    redis = await get_redis()
    raw = await redis.hgetall(key)
    out: dict[str, int] = {}
    if not raw:
        return out
    for field, value in raw.items():
        name = field.decode() if isinstance(field, bytes) else str(field)
        try:
            out[name] = int(value)
        except (TypeError, ValueError):
            continue
    return out


async def _count_online() -> int:
    try:
        redis = await get_redis()
        cutoff = time.time() - ONLINE_WINDOW_SECONDS
        await redis.zremrangebyscore(ONLINE_KEY, 0, cutoff)
        return int(await redis.zcard(ONLINE_KEY))
    except Exception:
        return 0


def _top_rows(data: dict[str, int], *, limit: int = 12, prefix: str | None = None) -> list[dict[str, Any]]:
    items = []
    for key, count in data.items():
        if prefix and not key.startswith(prefix):
            continue
        if prefix:
            key = key[len(prefix) :]
        items.append((key, count))
    items.sort(key=lambda row: -row[1])
    return [{"key": key, "count": count} for key, count in items[:limit]]


async def build_traffic_report(*, hours: int = 24, days: int = 7) -> dict[str, Any]:
    now = now_kyiv()
    hours = max(6, min(int(hours), 168))
    days = max(3, min(int(days), 30))

    hourly: list[dict[str, Any]] = []
    for offset in range(hours - 1, -1, -1):
        dt = now - timedelta(hours=offset)
        bucket = await _read_hash_ints(_hour_key(dt))
        hourly.append(
            {
                "label": dt.strftime("%H:00") if hours <= 24 else dt.strftime("%d.%m %H:00"),
                "total": bucket.get("total", 0),
                "unique": 0,
            }
        )

    daily: list[dict[str, Any]] = []
    geo_period: dict[str, int] = {}
    paths_period: dict[str, int] = {}
    hod_period: dict[str, int] = {str(h): 0 for h in range(24)}
    device_period: dict[str, int] = {}

    for offset in range(days - 1, -1, -1):
        dt = now - timedelta(days=offset)
        day_bucket = await _read_hash_ints(_day_key(dt))
        daily.append(
            {
                "label": dt.strftime("%d.%m"),
                "total": day_bucket.get("total", 0),
                "unique": day_bucket.get("unique", 0),
            }
        )
        for code, count in (await _read_hash_ints(_geo_day_key(dt))).items():
            geo_period[code] = geo_period.get(code, 0) + count
        for path, count in (await _read_hash_ints(_paths_day_key(dt))).items():
            paths_period[path] = paths_period.get(path, 0) + count
        for hour, count in (await _read_hash_ints(_hour_of_day_key(dt))).items():
            try:
                hod_period[str(int(hour))] = hod_period.get(str(int(hour)), 0) + count
            except ValueError:
                continue
        for field, count in (await _read_hash_ints(_day_key(dt))).items():
            if field.startswith("device:"):
                name = field[7:]
                device_period[name] = device_period.get(name, 0) + count

    today_bucket = await _read_hash_ints(_day_key(now))
    last_hour_bucket = await _read_hash_ints(_hour_key(now))
    period_total = sum(row["total"] for row in daily)
    period_unique = sum(row["unique"] for row in daily)
    online_now = await _count_online()

    countries = [
        {
            "code": code,
            "name": country_label(code),
            "count": count,
            "share": round(count / max(period_total, 1) * 100, 1),
        }
        for code, count in sorted(geo_period.items(), key=lambda row: -row[1])[:15]
    ]

    top_pages = [
        {
            "path": path,
            "label": path_label(path),
            "count": count,
            "share": round(count / max(period_total, 1) * 100, 1),
        }
        for path, count in sorted(paths_period.items(), key=lambda row: -row[1])[:15]
    ]

    time_of_day = [
        {"hour": hour, "label": f"{hour:02d}:00", "count": hod_period.get(str(hour), 0)}
        for hour in range(24)
    ]

    devices = [
        {"device": name, "count": count}
        for name, count in sorted(device_period.items(), key=lambda row: -row[1])
    ]

    return {
        "generated_at": now.isoformat(),
        "hours_window": hours,
        "days_window": days,
        "online_now": online_now,
        "today_total": today_bucket.get("total", 0),
        "today_unique": today_bucket.get("unique", 0),
        "last_hour_total": last_hour_bucket.get("total", 0),
        "period_total": period_total,
        "period_unique": period_unique,
        "avg_per_day": round(period_total / max(days, 1), 1),
        "avg_per_hour": round(period_total / max(days * 24, 1), 1),
        "hourly_chart": hourly,
        "daily_chart": daily,
        "countries": countries,
        "top_pages": top_pages,
        "time_of_day": time_of_day,
        "devices": devices,
    }
