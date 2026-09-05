"""Облік API-викликів на рівні моніторингу (SearchQuery) у Redis."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Any

from app.core.redis import get_redis
from app.core.timezone import now_kyiv

logger = logging.getLogger(__name__)

DAY_TTL_SECONDS = 60 * 60 * 24 * 95
MONITOR_SOURCES = ("auto_ria", "olx", "telegram_channels", "telegram_bot", "other")

_monitor_search_ids: ContextVar[list[str] | None] = ContextVar("monitor_search_ids", default=None)


def set_monitor_search_ids(search_ids: list[str]) -> object:
    return _monitor_search_ids.set([sid for sid in search_ids if sid])


def reset_monitor_search_ids(token: object) -> None:
    _monitor_search_ids.reset(token)  # type: ignore[arg-type]


def _day_key(search_id: str, dt: datetime | None = None) -> str:
    ts = dt or now_kyiv()
    return f"monitor_usage:day:{search_id}:{ts.strftime('%Y-%m-%d')}"


async def _incr_fields(search_id: str, fields: dict[str, float], *, dt: datetime | None = None) -> None:
    if not search_id or not fields:
        return
    try:
        redis = await get_redis()
        key = _day_key(search_id, dt)
        pipe = redis.pipeline(transaction=False)
        for field, amount in fields.items():
            if not amount:
                continue
            pipe.hincrbyfloat(key, field, float(amount))
        pipe.expire(key, DAY_TTL_SECONDS)
        await pipe.execute()
    except Exception:
        logger.warning("monitor_api_usage incr failed search=%s", search_id, exc_info=True)


def _split_amount(amount: float, search_ids: list[str]) -> float:
    if not search_ids:
        return 0.0
    return float(amount) / len(search_ids)


async def record_monitor_api_request(
    source: str,
    operation: str,
    *,
    success: bool = True,
    count: int = 1,
) -> None:
    """Дублює глобальний api_usage на кожен активний моніторинг у контексті парсера."""
    search_ids = _monitor_search_ids.get()
    if not search_ids:
        return

    src = source if source in MONITOR_SOURCES else "other"
    op = (operation or "other").strip().lower()[:48] or "other"
    amount = _split_amount(max(1, int(count)), search_ids)
    status = "ok" if success else "err"

    for search_id in search_ids:
        await _incr_fields(
            search_id,
            {
                "api:total": amount,
                f"api:{src}:total": amount,
                f"api:{src}:{op}": amount,
                f"api:{src}:{status}": amount,
            },
        )


async def record_monitor_cycle(
    search_ids: list[str],
    *,
    event: str,
    listings_found: int = 0,
    listings_new: int = 0,
) -> None:
    """Фіксує перевірку моніторингу (live API, кеш, live-pool)."""
    if not search_ids:
        return
    fields: dict[str, float] = {
        "cycles": 1.0,
        "listings_found": float(max(0, listings_found)),
        "listings_new": float(max(0, listings_new)),
    }
    if event == "cache_hit":
        fields["cache_hits"] = 1.0
    elif event == "pool_hit":
        fields["pool_hits"] = 1.0
    elif event == "live_api":
        fields["live_fetches"] = 1.0
    else:
        fields[f"event:{event}"] = 1.0

    for search_id in search_ids:
        await _incr_fields(search_id, fields)


async def _read_day_bucket(search_id: str, dt: datetime) -> dict[str, float]:
    redis = await get_redis()
    raw = await redis.hgetall(_day_key(search_id, dt))
    out: dict[str, float] = {}
    if not raw:
        return out
    for field, value in raw.items():
        key = field.decode() if isinstance(field, bytes) else str(field)
        try:
            out[key] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _sum_api_by_source(bucket: dict[str, float]) -> dict[str, dict[str, float]]:
    sources: dict[str, dict[str, float]] = {}
    for field, value in bucket.items():
        if not field.startswith("api:") or field == "api:total":
            continue
        parts = field.split(":", 2)
        if len(parts) != 3:
            continue
        _, source, op = parts
        block = sources.setdefault(source, {"total": 0.0, "ops": {}})
        if op in ("total", "ok", "err"):
            block[op] = block.get(op, 0.0) + value
        else:
            block["total"] = block.get("total", 0.0) + value
            ops = block.setdefault("ops", {})
            if isinstance(ops, dict):
                ops[op] = ops.get(op, 0.0) + value
    return sources


def _rollup_buckets(buckets: list[dict[str, float]]) -> dict[str, Any]:
    merged: dict[str, float] = {}
    for bucket in buckets:
        for key, value in bucket.items():
            merged[key] = merged.get(key, 0.0) + value

    api_total = merged.get("api:total", 0.0)
    sources = _sum_api_by_source(merged)
    daily: list[dict[str, Any]] = []

    return {
        "api_total": round(api_total, 1),
        "cycles": int(merged.get("cycles", 0)),
        "cache_hits": int(merged.get("cache_hits", 0)),
        "pool_hits": int(merged.get("pool_hits", 0)),
        "live_fetches": int(merged.get("live_fetches", 0)),
        "listings_found": int(merged.get("listings_found", 0)),
        "listings_new": int(merged.get("listings_new", 0)),
        "sources": {
            name: {
                "total": round(block.get("total", 0.0), 1),
                "ok": round(block.get("ok", 0.0), 1),
                "err": round(block.get("err", 0.0), 1),
                "ops": {
                    op: round(count, 1)
                    for op, count in sorted(
                        (block.get("ops") or {}).items(),
                        key=lambda item: -item[1],
                    )
                },
            }
            for name, block in sorted(sources.items(), key=lambda item: -item[1].get("total", 0))
        },
        "daily_chart": daily,
    }


async def batch_monitor_api_totals(search_ids: list[str], *, days: int = 1) -> dict[str, float]:
    """Сума api:total за N днів для списку моніторингів (один Redis round-trip на день)."""
    if not search_ids:
        return {}
    days = max(1, min(int(days), 90))
    now = now_kyiv()
    totals = {sid: 0.0 for sid in search_ids}
    try:
        redis = await get_redis()
        for offset in range(days):
            dt = now - timedelta(days=offset)
            pipe = redis.pipeline(transaction=False)
            keys = [_day_key(sid, dt) for sid in search_ids]
            for key in keys:
                pipe.hget(key, "api:total")
            values = await pipe.execute()
            for sid, raw in zip(search_ids, values):
                if raw is None:
                    continue
                try:
                    totals[sid] += float(raw)
                except (TypeError, ValueError):
                    continue
    except Exception:
        logger.warning("batch_monitor_api_totals failed", exc_info=True)
    return totals


async def build_monitor_usage_report(search_id: str, *, days: int = 7) -> dict[str, Any]:
    now = now_kyiv()
    days = max(1, min(int(days), 90))
    buckets: list[dict[str, float]] = []
    daily_chart: list[dict[str, Any]] = []

    for offset in range(days - 1, -1, -1):
        dt = now - timedelta(days=offset)
        bucket = await _read_day_bucket(search_id, dt)
        buckets.append(bucket)
        daily_chart.append(
            {
                "label": dt.strftime("%d.%m"),
                "api_total": round(bucket.get("api:total", 0.0), 1),
                "cycles": int(bucket.get("cycles", 0)),
                "listings_new": int(bucket.get("listings_new", 0)),
            }
        )

    rollup = _rollup_buckets(buckets)
    rollup["daily_chart"] = daily_chart
    rollup["days_window"] = days
    rollup["generated_at"] = now.isoformat()
    rollup["avg_api_per_day"] = round(rollup["api_total"] / days, 1)
    rollup["avg_cycles_per_day"] = round(rollup["cycles"] / days, 1)
    return rollup


def estimate_monitor_api_per_live_fetch(
    sources: list[str] | None,
    *,
    category: str = "all",
) -> dict[str, Any]:
    """Орієнтовні зовнішні виклики за один live-fetch (без кешу / live-pool)."""
    normalized = {s.strip().lower().replace(".", "_").replace(" ", "_") for s in (sources or [])}
    if not normalized:
        normalized = {"auto_ria", "olx"}

    per_source: dict[str, dict[str, int]] = {}
    total = 0

    if "auto_ria" in normalized:
        search_calls = 2 if category in {"all", "new"} else 1
        info_calls = 40  # AUTO_RIA_INFO_HYDRATE_CAP у моніторингу
        subtotal = search_calls + info_calls
        per_source["auto_ria"] = {
            "search": search_calls,
            "info": info_calls,
            "total": subtotal,
        }
        total += subtotal

    if "olx" in normalized:
        subtotal = 6  # 1 warm-up + до 5 сторінок offers API
        per_source["olx"] = {"search": subtotal, "total": subtotal}
        total += subtotal

    for key in ("imperiya", "car_market", "lubeavto", "reono", "udrive"):
        if key in normalized:
            subtotal = 3
            per_source[key] = {"search": subtotal, "total": subtotal}
            total += subtotal

    if "telegram" in normalized:
        per_source["telegram"] = {"db_query": 1, "total": 0}

    return {"per_source": per_source, "total": total}


def estimate_monitor_daily_api(
    sources: list[str] | None,
    *,
    category: str = "all",
    interval_seconds: int = 900,
    cache_hit_ratio: float = 0.0,
) -> dict[str, Any]:
    """Оцінка API на добу для одного моніторингу (одна filter-група)."""
    per_fetch = estimate_monitor_api_per_live_fetch(sources, category=category)
    cycles_per_day = max(1, int(86400 / max(60, interval_seconds)))
    live_fetches = max(0, cycles_per_day - int(cycles_per_day * min(max(cache_hit_ratio, 0.0), 0.95)))
    api_per_day = per_fetch["total"] * live_fetches

    return {
        "interval_seconds": interval_seconds,
        "cycles_per_day": cycles_per_day,
        "estimated_live_fetches_per_day": live_fetches,
        "api_per_live_fetch": per_fetch,
        "estimated_api_per_day": api_per_day,
        "note": (
            "Оцінка для окремого моніторингу без dedupe груп. "
            "Кеш (~5 хв) і live-pool зменшують фактичні виклики."
        ),
    }
