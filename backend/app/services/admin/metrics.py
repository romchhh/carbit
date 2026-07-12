from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.core.timezone import as_kyiv, now_kyiv, start_of_kyiv_day
from app.models.models import (
    Favorite,
    Listing,
    Notification,
    ParseRun,
    ParseRunStatus,
    SearchQuery,
    Source,
    User,
)
from app.services.parser.settings import get_parser_settings


async def check_database(db: AsyncSession) -> bool:
    try:
        await db.scalar(select(func.count()).select_from(User))
        return True
    except Exception:
        return False


async def check_kv_store() -> bool:
    try:
        kv = await get_redis()
        key = "__admin_health__"
        await kv.setex(key, 30, "1")
        return (await kv.get(key)) == "1"
    except Exception:
        return False


async def listings_by_source(db: AsyncSession) -> dict[str, int]:
    result: dict[str, int] = {s.value: 0 for s in Source}
    rows = await db.execute(
        select(Listing.source, func.count())
        .group_by(Listing.source)
    )
    for source, count in rows.all():
        key = source.value if hasattr(source, "value") else str(source)
        result[key] = count or 0
    return result


async def count_since(db: AsyncSession, model, column, since) -> int:
    return await db.scalar(
        select(func.count()).select_from(model).where(column >= since)
    ) or 0


async def daily_chart(db: AsyncSession, model, column, days: int = 7) -> list[dict]:
    today = start_of_kyiv_day(now_kyiv())
    chart = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        count = await db.scalar(
            select(func.count()).select_from(model).where(
                column >= day,
                column < next_day,
            )
        ) or 0
        chart.append({"date": day.strftime("%d.%m"), "count": count})
    return chart


async def parse_runs_chart(db: AsyncSession, days: int = 7) -> list[dict]:
    today = start_of_kyiv_day(now_kyiv())
    chart = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        base = select(ParseRun).where(
            ParseRun.started_at >= day,
            ParseRun.started_at < next_day,
        )
        runs = await db.scalars(base)
        items = runs.all()
        success = sum(1 for r in items if r.status == ParseRunStatus.success)
        failed = sum(1 for r in items if r.status == ParseRunStatus.failed)
        partial = sum(1 for r in items if r.status == ParseRunStatus.partial)
        found = sum(r.listings_found for r in items)
        new = sum(r.listings_new for r in items)
        chart.append({
            "date": day.strftime("%d.%m"),
            "runs": len(items),
            "success": success,
            "failed": failed,
            "partial": partial,
            "listings_found": found,
            "listings_new": new,
        })
    return chart


def integration_status() -> list[dict]:
    return [
        {
            "key": "auto_ria",
            "name": "AUTO.RIA API",
            "ok": bool(settings.AUTO_RIA_API_KEY.strip()),
            "detail": "Ключ налаштовано" if settings.AUTO_RIA_API_KEY.strip() else "AUTO_RIA_API_KEY відсутній",
        },
        {
            "key": "telegram_bot",
            "name": "Telegram Bot",
            "ok": bool(settings.TELEGRAM_BOT_TOKEN.strip()),
            "detail": settings.TELEGRAM_BOT_USERNAME or "Без username",
        },
        {
            "key": "telethon",
            "name": "Telethon (канали)",
            "ok": bool(settings.TELETHON_API_ID and settings.TELETHON_API_HASH.strip()),
            "detail": settings.TELETHON_NUMBER or "Номер не вказано",
        },
        {
            "key": "email",
            "name": "Email (Resend)",
            "ok": bool(settings.RESEND_API_KEY.strip()),
            "detail": settings.EMAIL_FROM,
        },
        {
            "key": "google_oauth",
            "name": "Google OAuth",
            "ok": bool(settings.GOOGLE_CLIENT_ID.strip() and settings.GOOGLE_CLIENT_SECRET.strip()),
            "detail": "Увімкнено" if settings.GOOGLE_CLIENT_ID.strip() else "Не налаштовано",
        },
    ]


async def telegram_channel_count(db: AsyncSession) -> int:
    try:
        from app.models.models import TelegramChannel

        return int(
            await db.scalar(
                select(func.count()).select_from(TelegramChannel).where(TelegramChannel.enabled.is_(True))
            )
            or 0
        )
    except Exception:
        return 0


async def data_quality_by_source(db: AsyncSession) -> dict[str, dict]:
    """% оголошень з валідним published_at / VIN / ціною по джерелах."""
    now = now_kyiv()
    # published_at «валідний», якщо не в майбутньому і не fallback «щойно» (старший за 2 хв від found_at
    # або явно відрізняється від now більше ніж на годину — евристика: year>0 і price>0 окремо)
    result: dict[str, dict] = {}
    for source in Source:
        total = await db.scalar(
            select(func.count()).select_from(Listing).where(Listing.source == source)
        ) or 0
        with_vin = await db.scalar(
            select(func.count())
            .select_from(Listing)
            .where(
                Listing.source == source,
                Listing.vin.isnot(None),
                func.length(Listing.vin) == 17,
            )
        ) or 0
        with_price = await db.scalar(
            select(func.count())
            .select_from(Listing)
            .where(Listing.source == source, Listing.price > 0)
        ) or 0
        with_published = await db.scalar(
            select(func.count())
            .select_from(Listing)
            .where(
                Listing.source == source,
                Listing.published_at.isnot(None),
                Listing.published_at < now,
            )
        ) or 0

        def pct(n: int) -> float:
            return round(100.0 * n / total, 1) if total else 0.0

        result[source.value] = {
            "total": total,
            "with_vin": with_vin,
            "with_price": with_price,
            "with_published_at": with_published,
            "pct_vin": pct(with_vin),
            "pct_price": pct(with_price),
            "pct_published_at": pct(with_published),
        }
    return result


async def build_analytics(db: AsyncSession) -> dict:
    now = now_kyiv()
    today = start_of_kyiv_day(now)
    week_ago = today - timedelta(days=7)

    by_source = await listings_by_source(db)
    total_listings = sum(by_source.values())
    duplicates = await db.scalar(
        select(func.count()).select_from(Listing).where(Listing.is_duplicate.is_(True))
    ) or 0
    active_searches = await db.scalar(
        select(func.count()).select_from(SearchQuery).where(SearchQuery.is_active.is_(True))
    ) or 0
    inactive_searches = await db.scalar(
        select(func.count()).select_from(SearchQuery).where(SearchQuery.is_active.is_(False))
    ) or 0
    favorites = await db.scalar(select(func.count()).select_from(Favorite)) or 0

    return {
        "listings_by_source": by_source,
        "total_listings": total_listings,
        "duplicate_listings": duplicates,
        "listings_today": await count_since(db, Listing, Listing.found_at, today),
        "listings_week": await count_since(db, Listing, Listing.found_at, week_ago),
        "notifications_today": await count_since(db, Notification, Notification.created_at, today),
        "notifications_week": await count_since(db, Notification, Notification.created_at, week_ago),
        "active_searches": active_searches,
        "inactive_searches": inactive_searches,
        "favorites_count": favorites,
        "listings_chart": await daily_chart(db, Listing, Listing.found_at),
        "notifications_chart": await daily_chart(db, Notification, Notification.created_at),
        "parse_runs_chart": await parse_runs_chart(db),
        "data_quality": await data_quality_by_source(db),
    }


async def build_system_status(db: AsyncSession) -> dict:
    parser_settings = await get_parser_settings()
    last_run = await db.scalar(
        select(ParseRun).order_by(ParseRun.started_at.desc()).limit(1)
    )

    last_run_out = None
    scheduler_status = "unknown"
    seconds_since_run: int | None = None

    if last_run:
        status = last_run.status.value if hasattr(last_run.status, "value") else str(last_run.status)
        last_run_out = {
            "id": last_run.id,
            "status": status,
            "started_at": last_run.started_at,
            "finished_at": last_run.finished_at,
            "listings_found": last_run.listings_found,
            "listings_new": last_run.listings_new,
            "notifications_sent": last_run.notifications_sent,
            "error": last_run.error,
        }
        delta = now_kyiv() - as_kyiv(last_run.started_at)
        seconds_since_run = int(delta.total_seconds())
        interval = parser_settings.get("interval_seconds", 3600)
        if last_run.status == ParseRunStatus.running:
            scheduler_status = "running"
        elif seconds_since_run <= interval * 1.5:
            scheduler_status = "ok"
        elif seconds_since_run <= interval * 3:
            scheduler_status = "delayed"
        else:
            scheduler_status = "stale"

    running_now = await db.scalar(
        select(func.count()).select_from(ParseRun).where(ParseRun.status == ParseRunStatus.running)
    ) or 0

    return {
        "database_ok": await check_database(db),
        "kv_store_ok": await check_kv_store(),
        "integrations": integration_status(),
        "parser_settings": parser_settings,
        "telegram_channels": await telegram_channel_count(db),
        "last_run": last_run_out,
        "scheduler_status": scheduler_status,
        "seconds_since_last_run": seconds_since_run,
        "running_parse_jobs": running_now,
        "frontend_url": settings.FRONTEND_URL,
        "debug_mode": settings.DEBUG,
    }
