from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.sqlite_retry import commit_session
from app.core.security import get_current_admin
from app.models.models import Listing, Notification, NotificationType, ParseRun, SearchListing, SearchQuery, User
from app.services.listings.serialize import listing_to_out
from app.services.parser.runner import run_parser_cycle
from app.services.parser.settings import get_parser_settings, save_parser_settings
from app.services.telegram_channels.channels import (
    count_channel_listings,
    create_channel,
    delete_channel,
    get_channel,
    list_channel_listings,
    list_channels,
    update_channel,
)
router = APIRouter(prefix="/admin/parser", tags=["admin-parser"])


class ParserSettingsOut(BaseModel):
    enabled: bool
    interval_seconds: int
    max_listings_per_group: int
    cache_ttl_seconds: int
    notify_telegram: bool
    telegram_enabled: bool
    telegram_history_limit: int
    telegram_worker_poll_seconds: int = 3
    telegram_channel_sync_seconds: int = 45
    notification_max_published_hours: int


class ParserSettingsUpdate(BaseModel):
    enabled: bool | None = None
    interval_seconds: int | None = Field(default=None, ge=60, le=86400)
    max_listings_per_group: int | None = Field(default=None, ge=5, le=100)
    cache_ttl_seconds: int | None = Field(default=None, ge=300, le=86400)
    notify_telegram: bool | None = None
    telegram_enabled: bool | None = None
    telegram_history_limit: int | None = Field(default=None, ge=10, le=3000)
    telegram_worker_poll_seconds: int | None = Field(default=None, ge=1, le=120)
    telegram_channel_sync_seconds: int | None = Field(default=None, ge=15, le=600)
    notification_max_published_hours: int | None = Field(default=None, ge=1, le=24)


class ParseRunOut(BaseModel):
    id: str
    status: str
    triggered_by: str
    filter_groups: int
    searches_processed: int
    listings_found: int
    listings_new: int
    notifications_sent: int
    error: str | None
    log: list
    started_at: datetime
    finished_at: datetime | None


def _run_out(run: ParseRun) -> ParseRunOut:
    status = run.status.value if hasattr(run.status, "value") else str(run.status)
    return ParseRunOut(
        id=run.id,
        status=status,
        triggered_by=run.triggered_by,
        filter_groups=run.filter_groups,
        searches_processed=run.searches_processed,
        listings_found=run.listings_found,
        listings_new=run.listings_new,
        notifications_sent=run.notifications_sent,
        error=run.error,
        log=run.log or [],
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


class ParserStatsOut(BaseModel):
    active_searches: int
    total_search_listings: int
    total_listings: int
    total_telegram_sent: int
    last_run: ParseRunOut | None
    settings: ParserSettingsOut
    monitor_api_estimate: MonitorApiEstimateOut | None = None


class ParserNotificationOut(BaseModel):
    id: str
    sent_at: datetime
    user_id: str
    user_name: str
    user_email: str
    telegram_username: str | None
    search_id: str | None
    search_name: str | None
    listing_id: str | None
    listing_title: str
    listing_brand: str | None
    listing_model: str | None
    listing_year: int | None
    listing_price: int | None
    listing_region: str | None
    listing_source: str | None
    listing_url: str | None
    listing_image: str | None


class AdminActiveSearchOut(BaseModel):
    id: str
    name: str
    user_id: str
    user_name: str
    user_email: str
    telegram_connected: bool
    telegram_username: str | None
    telegram_has_chat_id: bool
    brand: str | None
    model: str | None
    region: str | None
    sources: list[str] | None
    is_active: bool
    new_count: int
    total_count: int
    telegram_sent_count: int
    last_checked_at: datetime | None
    created_at: datetime
    api_today: float = 0
    api_7d: float = 0


class MonitorApiUsageOut(BaseModel):
    api_total: float
    avg_api_per_day: float
    avg_cycles_per_day: float
    cycles: int
    cache_hits: int
    pool_hits: int
    live_fetches: int
    listings_found: int
    listings_new: int
    sources: dict
    daily_chart: list[dict]
    days_window: int
    generated_at: str


class MonitorApiEstimateOut(BaseModel):
    interval_seconds: int
    cycles_per_day: int
    estimated_live_fetches_per_day: int
    estimated_api_per_day: int
    api_per_live_fetch: dict
    note: str


class AdminSearchDetailOut(BaseModel):
    search: AdminActiveSearchOut
    listings: list[AdminSearchListingOut]
    telegram_sent_total: int
    telegram_pending: int
    api_usage_7d: MonitorApiUsageOut | None = None
    api_usage_30d: MonitorApiUsageOut | None = None
    api_estimate_daily: MonitorApiEstimateOut | None = None
    listing_id: str
    title: str
    brand: str
    model: str
    year: int
    price: int
    currency: str
    region: str
    source: str
    url: str
    image: str | None
    is_new: bool
    first_seen_at: datetime
    notified_at: datetime | None
    telegram_sent: bool
    telegram_sent_at: datetime | None
    telegram_issue: str | None = None


class AdminSearchListingOut(BaseModel):
    data = filters if isinstance(filters, dict) else {}
    brand = (data.get("brand") or "").strip() or None
    model = (data.get("model") or "").strip() or None
    region = (data.get("region") or "").strip() or None
    sources = data.get("sources")
    if isinstance(sources, list):
        sources = [str(s) for s in sources if s]
    else:
        sources = None
    return brand, model, region, sources


async def _search_telegram_sent_count(db: AsyncSession, search_id: str) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.search_id == search_id,
                Notification.type == NotificationType.listing_match,
                Notification.sent_telegram.is_(True),
            )
        )
        or 0
    )


def _telegram_issue_hint(
    user: User,
    notif: Notification | None,
    *,
    telegram_sent: bool,
) -> str | None:
    if telegram_sent:
        return None
    if not user.telegram_connected:
        return "no_bot_link"
    if not user.telegram_id:
        return "bot_start_required"
    if notif is None:
        return "not_attempted"
    payload = notif.payload or {}
    if payload.get("telegram_skipped_no_chat_id"):
        return "bot_start_required"
    if payload.get("telegram_skipped_already_notified"):
        return "skipped_duplicate_car"
    if payload.get("telegram_skipped_duplicate"):
        return "skipped_vin_mirror"
    return "send_failed"


async def _monitor_api_totals_batch(search_ids: list[str], *, days: int = 1) -> dict[str, float]:
    from app.services.admin.monitor_api_usage import batch_monitor_api_totals

    return await batch_monitor_api_totals(search_ids, days=days)


async def _active_search_out(
    db: AsyncSession,
    search: SearchQuery,
    user: User,
    *,
    api_today: float = 0,
    api_7d: float = 0,
) -> AdminActiveSearchOut:
    brand, model, region, sources = _filters_summary(search.filters)
    return AdminActiveSearchOut(
        id=search.id,
        name=search.name,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        telegram_connected=bool(user.telegram_connected),
        telegram_username=user.telegram_username,
        telegram_has_chat_id=bool(user.telegram_id),
        brand=brand,
        model=model,
        region=region,
        sources=sources,
        is_active=bool(search.is_active),
        new_count=int(search.new_count or 0),
        total_count=int(search.total_count or 0),
        telegram_sent_count=await _search_telegram_sent_count(db, search.id),
        last_checked_at=search.last_checked_at,
        created_at=search.created_at,
        api_today=api_today,
        api_7d=api_7d,
    )


@router.get("/settings", response_model=ParserSettingsOut)
async def parser_settings(_admin=Depends(get_current_admin)):
    data = await get_parser_settings()
    return ParserSettingsOut(**data)


@router.patch("/settings", response_model=ParserSettingsOut)
async def update_parser_settings(body: ParserSettingsUpdate, _admin=Depends(get_current_admin)):
    data = await save_parser_settings(body.model_dump(exclude_none=True))
    return ParserSettingsOut(**data)


@router.get("/stats", response_model=ParserStatsOut)
async def parser_stats(db: AsyncSession = Depends(get_db), _admin=Depends(get_current_admin)):
    active = await db.scalar(
        select(func.count()).select_from(SearchQuery).where(SearchQuery.is_active.is_(True))
    )
    total_links = await db.scalar(select(func.count()).select_from(SearchListing))
    total_listings = await db.scalar(select(func.count()).select_from(Listing))
    total_telegram = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.sent_telegram.is_(True),
            Notification.type == NotificationType.listing_match,
        )
    )
    last = await db.scalar(select(ParseRun).order_by(desc(ParseRun.started_at)).limit(1))
    settings = await get_parser_settings()
    from app.services.admin.monitor_api_usage import estimate_monitor_daily_api

    estimate_raw = estimate_monitor_daily_api(
        ["auto_ria", "olx"],
        category="all",
        interval_seconds=int(settings.get("interval_seconds") or 900),
    )
    return ParserStatsOut(
        active_searches=active or 0,
        total_search_listings=total_links or 0,
        total_listings=total_listings or 0,
        total_telegram_sent=total_telegram or 0,
        last_run=_run_out(last) if last else None,
        settings=ParserSettingsOut(**settings),
        monitor_api_estimate=MonitorApiEstimateOut(**estimate_raw),
    )


@router.get("/searches", response_model=list[AdminActiveSearchOut])
async def list_parser_searches(
    active_only: bool = Query(True),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    stmt = (
        select(SearchQuery, User)
        .join(User, User.id == SearchQuery.user_id)
        .order_by(desc(SearchQuery.created_at))
        .limit(limit)
    )
    if active_only:
        stmt = stmt.where(SearchQuery.is_active.is_(True))

    rows = (await db.execute(stmt)).all()
    search_ids = [search.id for search, _user in rows]
    api_today_map = await _monitor_api_totals_batch(search_ids, days=1)
    api_7d_map = await _monitor_api_totals_batch(search_ids, days=7)
    out: list[AdminActiveSearchOut] = []
    for search, user in rows:
        out.append(
            await _active_search_out(
                db,
                search,
                user,
                api_today=api_today_map.get(search.id, 0.0),
                api_7d=api_7d_map.get(search.id, 0.0),
            )
        )
    return out


@router.get("/searches/{search_id}", response_model=AdminSearchDetailOut)
async def get_parser_search_detail(
    search_id: str,
    listings_limit: int = Query(80, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    row = await db.execute(
        select(SearchQuery, User)
        .join(User, User.id == SearchQuery.user_id)
        .where(SearchQuery.id == search_id)
    )
    pair = row.first()
    if not pair:
        raise HTTPException(404, "Пошук не знайдено")
    search, user = pair

    sent_rows = (
        await db.execute(
            select(Notification.listing_id, func.max(Notification.created_at))
            .where(
                Notification.search_id == search_id,
                Notification.type == NotificationType.listing_match,
                Notification.sent_telegram.is_(True),
            )
            .group_by(Notification.listing_id)
        )
    ).all()
    sent_map: dict[str, datetime] = {lid: ts for lid, ts in sent_rows if lid and ts}

    sl_rows = (
        await db.execute(
            select(SearchListing, Listing)
            .join(Listing, Listing.id == SearchListing.listing_id)
            .where(SearchListing.search_id == search_id)
            .order_by(desc(SearchListing.first_seen_at))
            .limit(listings_limit)
        )
    ).all()

    listing_ids = [listing.id for _, listing in sl_rows]
    latest_notif: dict[str, Notification] = {}
    if listing_ids:
        notif_rows = (
            await db.scalars(
                select(Notification)
                .where(
                    Notification.search_id == search_id,
                    Notification.listing_id.in_(listing_ids),
                    Notification.type == NotificationType.listing_match,
                )
                .order_by(desc(Notification.created_at))
            )
        ).all()
        for notif in notif_rows:
            if notif.listing_id and notif.listing_id not in latest_notif:
                latest_notif[notif.listing_id] = notif

    listings_out: list[AdminSearchListingOut] = []
    telegram_sent_total = len(sent_map)
    telegram_pending = 0

    for sl, listing in sl_rows:
        sent_at = sent_map.get(listing.id)
        telegram_sent = sent_at is not None
        if sl.is_new and not telegram_sent:
            telegram_pending += 1
        notif = latest_notif.get(listing.id)
        issue = _telegram_issue_hint(user, notif, telegram_sent=telegram_sent)
        source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
        images = listing.images or []
        listings_out.append(
            AdminSearchListingOut(
                listing_id=listing.id,
                title=listing.title,
                brand=listing.brand,
                model=listing.model,
                year=int(listing.year or 0),
                price=int(listing.price or 0),
                currency=listing.currency or "UAH",
                region=listing.region,
                source=source,
                url=listing.url,
                image=images[0] if images else None,
                is_new=bool(sl.is_new),
                first_seen_at=sl.first_seen_at,
                notified_at=sl.notified_at,
                telegram_sent=telegram_sent,
                telegram_sent_at=sent_at,
                telegram_issue=issue,
            )
        )

    search_out = await _active_search_out(db, search, user)
    from app.services.admin.monitor_api_usage import (
        build_monitor_usage_report,
        estimate_monitor_daily_api,
    )

    usage_7d = await build_monitor_usage_report(search_id, days=7)
    usage_30d = await build_monitor_usage_report(search_id, days=30)
    filters = search.filters if isinstance(search.filters, dict) else {}
    category = str(filters.get("category") or "all")
    sources = filters.get("sources") if isinstance(filters.get("sources"), list) else None
    settings = await get_parser_settings()
    estimate_raw = estimate_monitor_daily_api(
        [str(s) for s in sources] if sources else None,
        category=category,
        interval_seconds=int(settings.get("interval_seconds") or 900),
    )

    return AdminSearchDetailOut(
        search=search_out,
        listings=listings_out,
        telegram_sent_total=telegram_sent_total,
        telegram_pending=telegram_pending,
        api_usage_7d=MonitorApiUsageOut(**usage_7d),
        api_usage_30d=MonitorApiUsageOut(**usage_30d),
        api_estimate_daily=MonitorApiEstimateOut(**estimate_raw),
    )


@router.post("/searches/{search_id}/deliver-telegram")
async def deliver_search_telegram(
    search_id: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Примусова догонка Telegram для нових авто в моніторингу (окремий користувач)."""
    search = await db.get(SearchQuery, search_id)
    if not search:
        raise HTTPException(404, "Пошук не знайдено")
    from app.services.notifications.service import deliver_pending_monitor_telegram

    delivered = 0
    for _ in range(10):
        batch = await deliver_pending_monitor_telegram(
            db,
            search_ids=[search_id],
            limit=50,
            persist_each=True,
        )
        if not batch:
            break
        delivered += batch
    await commit_session(db)
    return {"delivered": delivered}


@router.get("/runs", response_model=list[ParseRunOut])
async def parser_runs(
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    rows = await db.scalars(select(ParseRun).order_by(desc(ParseRun.started_at)).limit(limit))
    return [_run_out(row) for row in rows.all()]


@router.get("/listings")
async def parser_listings(
    limit: int = Query(40, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    rows = await db.scalars(select(Listing).order_by(desc(Listing.found_at)).limit(limit))
    return [listing_to_out(item).model_dump() for item in rows.all()]


def _notification_out(
    notification: Notification,
    user: User,
    listing: Listing | None,
    search: SearchQuery | None,
) -> ParserNotificationOut:
    source = None
    image = None
    if listing:
        source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
        images = listing.images or []
        image = images[0] if images else None

    return ParserNotificationOut(
        id=notification.id,
        sent_at=notification.created_at,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        telegram_username=user.telegram_username,
        search_id=search.id if search else notification.search_id,
        search_name=search.name if search else None,
        listing_id=listing.id if listing else notification.listing_id,
        listing_title=listing.title if listing else notification.title,
        listing_brand=listing.brand if listing else None,
        listing_model=listing.model if listing else None,
        listing_year=listing.year if listing else notification.payload.get("year"),
        listing_price=listing.price if listing else notification.payload.get("price"),
        listing_region=listing.region if listing else notification.payload.get("region"),
        listing_source=source or notification.payload.get("source"),
        listing_url=listing.url if listing else notification.payload.get("url"),
        listing_image=image,
    )


@router.get("/notifications", response_model=list[ParserNotificationOut])
async def parser_notifications(
    limit: int = Query(50, ge=1, le=200),
    run_id: str | None = Query(default=None),
    search_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    stmt = (
        select(Notification, User, Listing, SearchQuery)
        .join(User, Notification.user_id == User.id)
        .outerjoin(Listing, Notification.listing_id == Listing.id)
        .outerjoin(SearchQuery, Notification.search_id == SearchQuery.id)
        .where(
            Notification.sent_telegram.is_(True),
            Notification.type == NotificationType.listing_match,
        )
        .order_by(desc(Notification.created_at))
        .limit(limit)
    )

    if run_id:
        run = await db.get(ParseRun, run_id)
        if run:
            stmt = stmt.where(Notification.created_at >= run.started_at)
            if run.finished_at:
                stmt = stmt.where(Notification.created_at <= run.finished_at)

    if search_id:
        stmt = stmt.where(Notification.search_id == search_id)

    rows = await db.execute(stmt)
    return [
        _notification_out(notification, user, listing, search)
        for notification, user, listing, search in rows.all()
    ]


@router.post("/run", response_model=ParseRunOut)
async def trigger_parser_run(_admin=Depends(get_current_admin)):
    async with AsyncSessionLocal() as db:
        run = await run_parser_cycle(db, triggered_by="admin")
        await db.commit()
        await db.refresh(run)
        return _run_out(run)


ParserSource = Literal["auto_ria", "olx", "telegram"]


@router.post("/run/{source}", response_model=ParseRunOut)
async def trigger_parser_run_source(source: ParserSource, _admin=Depends(get_current_admin)):
    async with AsyncSessionLocal() as db:
        run = await run_parser_cycle(
            db,
            triggered_by=f"admin:{source}",
            sources=[source],
        )
        await db.commit()
        await db.refresh(run)
        return _run_out(run)


class TelegramChannelOut(BaseModel):
    id: str
    username: str
    title: str | None
    enabled: bool
    sort_order: int
    listings_count: int
    created_at: datetime


class TelegramChannelCreate(BaseModel):
    username: str = Field(min_length=2, max_length=120)
    title: str | None = Field(default=None, max_length=200)
    enabled: bool = True


class TelegramChannelUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=120)
    title: str | None = Field(default=None, max_length=200)
    enabled: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=10_000)


class TelegramWorkerStatusOut(BaseModel):
    telegram_enabled: bool
    telethon_configured: bool
    worker_online: bool
    worker_heartbeat_age_seconds: float | None
    interval_seconds: int
    telegram_worker_poll_seconds: int
    telegram_channel_sync_seconds: int
    telegram_history_limit: int
    keyword_queue: dict[str, int]
    schedule_hint: str


class TelethonSessionUserOut(BaseModel):
    id: int
    first_name: str
    username: str | None = None


class TelethonSessionStatusOut(BaseModel):
    telethon_configured: bool
    phone_configured: bool
    phone_masked: str
    session_file: str
    session_exists: bool
    authorized: bool
    user: TelethonSessionUserOut | None = None
    error: str | None = None
    error_code: str | None = None
    auth_step: str | None = None
    session_note: str | None = None
    worker_holds_session: bool = False


class TelethonAuthCodeIn(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class TelethonAuthPasswordIn(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class TelethonAuthResultOut(BaseModel):
    status: str
    phone_masked: str | None = None
    user: TelethonSessionUserOut | None = None


class TelethonSessionResetOut(BaseModel):
    removed: list[str]
    session_file: str


@router.get("/telethon/session", response_model=TelethonSessionStatusOut)
async def telethon_session_status(_admin=Depends(get_current_admin)):
    from app.services.telegram_channels.telethon_auth import get_telethon_session_status

    data = await get_telethon_session_status()
    user = data.get("user")
    return TelethonSessionStatusOut(
        **{
            **data,
            "user": TelethonSessionUserOut(**user) if user else None,
        }
    )


@router.post("/telethon/session/reset", response_model=TelethonSessionResetOut)
async def telethon_session_reset(_admin=Depends(get_current_admin)):
    from app.services.telegram_channels.telethon_auth import reset_telethon_session

    return TelethonSessionResetOut(**await reset_telethon_session())


@router.post("/telethon/auth/send-code", response_model=TelethonAuthResultOut)
async def telethon_auth_send_code(_admin=Depends(get_current_admin)):
    from app.services.telegram_channels.telethon_auth import send_telethon_login_code

    data = await send_telethon_login_code()
    user = data.get("user")
    return TelethonAuthResultOut(
        status=data["status"],
        phone_masked=data.get("phone_masked"),
        user=TelethonSessionUserOut(**user) if user else None,
    )


@router.post("/telethon/auth/sign-in", response_model=TelethonAuthResultOut)
async def telethon_auth_sign_in(body: TelethonAuthCodeIn, _admin=Depends(get_current_admin)):
    from app.services.telegram_channels.telethon_auth import confirm_telethon_code

    data = await confirm_telethon_code(body.code)
    user = data.get("user")
    return TelethonAuthResultOut(
        status=data["status"],
        phone_masked=data.get("phone_masked"),
        user=TelethonSessionUserOut(**user) if user else None,
    )


@router.post("/telethon/auth/password", response_model=TelethonAuthResultOut)
async def telethon_auth_password(body: TelethonAuthPasswordIn, _admin=Depends(get_current_admin)):
    from app.services.telegram_channels.telethon_auth import confirm_telethon_password

    data = await confirm_telethon_password(body.password)
    user = data.get("user")
    return TelethonAuthResultOut(
        status=data["status"],
        phone_masked=data.get("phone_masked"),
        user=TelethonSessionUserOut(**user) if user else None,
    )


@router.get("/telegram/status", response_model=TelegramWorkerStatusOut)
async def telegram_worker_status(_admin=Depends(get_current_admin)):
    from app.services.telegram_channels.admin_status import get_telegram_worker_status

    return TelegramWorkerStatusOut(**await get_telegram_worker_status())


@router.post("/listings/fix-duplicate-links")
async def fix_duplicate_links(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    from app.services.listings.duplicates import clear_invalid_duplicate_links

    result = await clear_invalid_duplicate_links(db)
    await db.commit()
    return result


@router.post("/telegram/reset-stuck-jobs")
async def reset_stuck_keyword_jobs(_admin=Depends(get_current_admin)):
    from app.services.telegram_channels.bootstrap import ensure_parser_path

    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    store = ChannelMediaStore()
    stuck = store.reset_stuck_running_jobs(older_than_seconds=0)
    return {"reset": stuck}


async def _channel_out(db: AsyncSession, channel) -> TelegramChannelOut:
    return TelegramChannelOut(
        id=channel.id,
        username=channel.username,
        title=channel.title,
        enabled=channel.enabled,
        sort_order=channel.sort_order,
        listings_count=await count_channel_listings(db, channel.username),
        created_at=channel.created_at,
    )


@router.get("/channels", response_model=list[TelegramChannelOut])
async def list_telegram_channels(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    channels = await list_channels(db)
    return [await _channel_out(db, channel) for channel in channels]


@router.post("/channels", response_model=TelegramChannelOut)
async def create_telegram_channel(
    body: TelegramChannelCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    try:
        channel = await create_channel(
            db,
            username=body.username,
            title=body.title,
            enabled=body.enabled,
        )
        await db.commit()
        await db.refresh(channel)
        return await _channel_out(db, channel)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.patch("/channels/{channel_id}", response_model=TelegramChannelOut)
async def update_telegram_channel(
    channel_id: str,
    body: TelegramChannelUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    channel = await get_channel(db, channel_id)
    if not channel:
        raise HTTPException(404, "Канал не знайдено")
    try:
        channel = await update_channel(
            db,
            channel,
            username=body.username,
            title=body.title,
            enabled=body.enabled,
            sort_order=body.sort_order,
        )
        await db.commit()
        await db.refresh(channel)
        return await _channel_out(db, channel)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.delete("/channels/{channel_id}", status_code=204)
async def delete_telegram_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    channel = await get_channel(db, channel_id)
    if not channel:
        raise HTTPException(404, "Канал не знайдено")
    await delete_channel(db, channel)
    await db.commit()


@router.get("/channels/{channel_id}/listings")
async def telegram_channel_listings(
    channel_id: str,
    limit: int = Query(40, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    channel = await get_channel(db, channel_id)
    if not channel:
        raise HTTPException(404, "Канал не знайдено")
    rows = await list_channel_listings(db, channel.username, limit=limit)
    return [listing_to_out(item).model_dump() for item in rows]
