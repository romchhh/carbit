from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
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
    return ParserStatsOut(
        active_searches=active or 0,
        total_search_listings=total_links or 0,
        total_listings=total_listings or 0,
        total_telegram_sent=total_telegram or 0,
        last_run=_run_out(last) if last else None,
        settings=ParserSettingsOut(**settings),
    )


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
