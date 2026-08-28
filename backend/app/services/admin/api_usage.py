"""Облік зовнішніх API-запитів (AUTO.RIA, OLX, Telegram) у Redis для адмін-дашборду."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from app.core.redis import get_redis
from app.core.timezone import now_kyiv

logger = logging.getLogger(__name__)

HOUR_TTL_SECONDS = 60 * 60 * 24 * 35  # 35 днів
DAY_TTL_SECONDS = 60 * 60 * 24 * 95  # 95 днів
MONTH_TTL_SECONDS = 60 * 60 * 24 * 400  # ~13 місяців

SOURCES = ("auto_ria", "olx", "telegram_channels", "telegram_bot")


def _hour_key(source: str, dt: datetime | None = None) -> str:
    ts = dt or now_kyiv()
    return f"api_usage:hour:{source}:{ts.strftime('%Y-%m-%d-%H')}"


def _day_key(source: str, dt: datetime | None = None) -> str:
    ts = dt or now_kyiv()
    return f"api_usage:day:{source}:{ts.strftime('%Y-%m-%d')}"


def _month_key(source: str, dt: datetime | None = None) -> str:
    ts = dt or now_kyiv()
    return f"api_usage:month:{source}:{ts.strftime('%Y-%m')}"


async def record_api_request(
    source: str,
    operation: str,
    *,
    success: bool = True,
    count: int = 1,
) -> None:
    """Збільшити лічильник запитів для source/operation (fire-and-forget safe)."""
    if source not in SOURCES:
        return
    op = (operation or "other").strip().lower()[:48] or "other"
    amount = max(1, int(count))
    try:
        redis = await get_redis()
        now = now_kyiv()
        hour_key = _hour_key(source, now)
        day_key = _day_key(source, now)
        month_key = _month_key(source, now)
        for key, ttl in (
            (hour_key, HOUR_TTL_SECONDS),
            (day_key, DAY_TTL_SECONDS),
            (month_key, MONTH_TTL_SECONDS),
        ):
            await redis.hincrby(key, "total", amount)
            await redis.hincrby(key, "ok" if success else "err", amount)
            await redis.hincrby(key, f"op:{op}", amount)
            await redis.expire(key, ttl)
        if source == "auto_ria":
            from app.services.auto_ria.quota_alerts import schedule_auto_ria_quota_check

            schedule_auto_ria_quota_check()
    except Exception:
        logger.warning("api_usage record failed source=%s op=%s", source, op, exc_info=True)


def auto_ria_operation(path: str) -> str:
    p = (path or "").split("?", 1)[0].strip().lower()
    if p == "/auto/search":
        return "search"
    if p == "/auto/info":
        return "info"
    if p.startswith("/auto/fotos"):
        return "fotos"
    if p == "/auto/new/search":
        return "new_search"
    if p.startswith("/auto/new/auto"):
        return "new_info"
    if "/marks" in p or "/models" in p:
        return "catalog"
    return "other"


def olx_operation(url: str) -> str:
    u = (url or "").lower()
    if "/offers/" in u or "offers" in u and "api" in u:
        return "search"
    if "/ad/" in u or "/d/uk/" in u or "/obyavlenie/" in u:
        return "details"
    return "html"


async def _read_hash_totals(key: str) -> dict[str, Any]:
    redis = await get_redis()
    raw = await redis.hgetall(key)
    out: dict[str, Any] = {"total": 0, "ok": 0, "err": 0, "ops": {}}
    if not raw:
        return out
    ops: dict[str, int] = {}
    for field, value in raw.items():
        f = field.decode() if isinstance(field, bytes) else str(field)
        try:
            n = int(value)
        except (TypeError, ValueError):
            continue
        if f == "total":
            out["total"] = n
        elif f == "ok":
            out["ok"] = n
        elif f == "err":
            out["err"] = n
        elif f.startswith("op:"):
            ops[f[3:]] = n
    out["ops"] = ops
    return out


async def get_auto_ria_quota_usage() -> dict[str, int]:
    """Поточне використання AUTO.RIA для годинного/місячного вікна."""
    now = now_kyiv()
    hour = await _read_hash_totals(_hour_key("auto_ria", now))
    month = await _read_hash_totals(_month_key("auto_ria", now))
    return {
        "hour_used": int(hour.get("total") or 0),
        "month_used": int(month.get("total") or 0),
    }


async def build_api_usage_report(*, hours: int = 24, days: int = 7) -> dict[str, Any]:
    """Зведення для адмінки: KPI, погодинні та денні графіки, розбивка по операціях."""
    now = now_kyiv()
    sources_out: dict[str, Any] = {}

    for source in SOURCES:
        hourly: list[dict[str, Any]] = []
        for offset in range(hours - 1, -1, -1):
            dt = now - timedelta(hours=offset)
            label = dt.strftime("%H:00") if hours <= 24 else dt.strftime("%d.%m %H:00")
            bucket = await _read_hash_totals(_hour_key(source, dt))
            hourly.append({"label": label, "total": bucket.get("total", 0), "ok": bucket.get("ok", 0), "err": bucket.get("err", 0)})

        daily: list[dict[str, Any]] = []
        period_ops: dict[str, int] = {}
        for offset in range(days - 1, -1, -1):
            dt = now - timedelta(days=offset)
            label = dt.strftime("%d.%m")
            bucket = await _read_hash_totals(_day_key(source, dt))
            daily.append({"label": label, "total": bucket.get("total", 0), "ok": bucket.get("ok", 0), "err": bucket.get("err", 0)})
            for op_name, op_count in (bucket.get("ops") or {}).items():
                period_ops[op_name] = period_ops.get(op_name, 0) + op_count

        today = await _read_hash_totals(_day_key(source, now))
        last_hour = await _read_hash_totals(_hour_key(source, now))
        month_bucket = await _read_hash_totals(_month_key(source, now)) if source == "auto_ria" else {}

        ops_raw = today.get("ops") or {}
        operations_today = [
            {"operation": name, "count": count}
            for name, count in sorted(ops_raw.items(), key=lambda x: -x[1])
        ]
        operations_period = [
            {"operation": name, "count": count}
            for name, count in sorted(period_ops.items(), key=lambda x: -x[1])
        ]

        period_total = sum(d["total"] for d in daily)
        period_ok = sum(d["ok"] for d in daily)
        period_err = sum(d["err"] for d in daily)
        avg_per_day = round(period_total / max(days, 1), 1)
        avg_per_hour = round(period_total / max(days * 24, 1), 1)

        sources_out[source] = {
            "today_total": today.get("total", 0),
            "today_ok": today.get("ok", 0),
            "today_err": today.get("err", 0),
            "month_total": month_bucket.get("total", 0) if source == "auto_ria" else None,
            "period_total": period_total,
            "period_ok": period_ok,
            "period_err": period_err,
            "last_hour_total": last_hour.get("total", 0),
            "avg_per_hour": avg_per_hour,
            "avg_per_day": avg_per_day,
            "hourly_chart": hourly,
            "daily_chart": daily,
            "operations_today": operations_today,
            "operations_period": operations_period,
        }

    return {
        "generated_at": now.isoformat(),
        "hours_window": hours,
        "days_window": days,
        "sources": sources_out,
    }
