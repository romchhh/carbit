from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.models import Listing, Source
from app.schemas.schemas import ListingOut
from app.services.admin.metrics import build_analytics, build_system_status
from app.services.listings.serialize import listing_to_out

router = APIRouter(prefix="/admin", tags=["admin-ops"])


class ChartPoint(BaseModel):
    date: str
    count: int


class ParseRunChartPoint(BaseModel):
    date: str
    runs: int
    success: int
    failed: int
    partial: int
    listings_found: int
    listings_new: int


class AdminAnalyticsOut(BaseModel):
    listings_by_source: dict[str, int]
    total_listings: int
    duplicate_listings: int
    listings_today: int
    listings_week: int
    notifications_today: int
    notifications_week: int
    active_searches: int
    inactive_searches: int
    favorites_count: int
    listings_chart: list[ChartPoint]
    notifications_chart: list[ChartPoint]
    parse_runs_chart: list[ParseRunChartPoint]


class IntegrationStatus(BaseModel):
    key: str
    name: str
    ok: bool
    detail: str


class LastRunSummary(BaseModel):
    id: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    listings_found: int
    listings_new: int
    notifications_sent: int
    error: str | None


class AdminSystemOut(BaseModel):
    database_ok: bool
    kv_store_ok: bool
    integrations: list[IntegrationStatus]
    parser_settings: dict
    telegram_channels: int
    last_run: LastRunSummary | None
    scheduler_status: str
    seconds_since_last_run: int | None
    running_parse_jobs: int
    frontend_url: str
    debug_mode: bool


class AdminListingOut(BaseModel):
    id: str
    external_id: str
    source: str
    title: str
    brand: str
    model: str
    year: int
    price: int
    region: str
    url: str
    image: str | None
    is_duplicate: bool
    found_at: datetime


class PaginatedListings(BaseModel):
    items: list[AdminListingOut]
    total: int
    page: int
    per_page: int


@router.get("/analytics", response_model=AdminAnalyticsOut)
async def admin_analytics(
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await build_analytics(db)
    return AdminAnalyticsOut(**data)


@router.get("/system", response_model=AdminSystemOut)
async def admin_system(
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await build_system_status(db)
    return AdminSystemOut(**data)


@router.get("/listings", response_model=PaginatedListings)
async def admin_listings(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    source: str | None = None,
    search: str = Query(""),
    duplicates_only: bool = False,
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(Listing)
    count_q = select(func.count()).select_from(Listing)

    if source:
        try:
            src = Source(source)
            q = q.where(Listing.source == src)
            count_q = count_q.where(Listing.source == src)
        except ValueError:
            pass

    if duplicates_only:
        q = q.where(Listing.is_duplicate.is_(True))
        count_q = count_q.where(Listing.is_duplicate.is_(True))

    if search.strip():
        term = f"%{search.strip()}%"
        filt = or_(
            Listing.title.ilike(term),
            Listing.brand.ilike(term),
            Listing.model.ilike(term),
            Listing.region.ilike(term),
            Listing.external_id.ilike(term),
        )
        q = q.where(filt)
        count_q = count_q.where(filt)

    total = await db.scalar(count_q) or 0
    rows = await db.scalars(
        q.order_by(desc(Listing.found_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    items = []
    for row in rows.all():
        out = listing_to_out(row)
        items.append(AdminListingOut(
            id=out.id,
            external_id=row.external_id,
            source=out.source,
            title=out.title,
            brand=out.brand,
            model=out.model,
            year=out.year,
            price=out.price,
            region=out.region,
            url=out.url,
            image=out.images[0] if out.images else None,
            is_duplicate=row.is_duplicate,
            found_at=row.found_at,
        ))

    return PaginatedListings(items=items, total=total, page=page, per_page=per_page)


@router.get("/listings/{listing_id}", response_model=ListingOut)
async def admin_listing_detail(
    listing_id: str,
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing_to_out(listing)


class ApiUsageChartPoint(BaseModel):
    label: str
    total: int
    ok: int
    err: int


class ApiUsageOperationRow(BaseModel):
    operation: str
    count: int


class ApiUsageSourceOut(BaseModel):
    today_total: int
    today_ok: int
    today_err: int
    period_total: int
    period_ok: int
    period_err: int
    last_hour_total: int
    avg_per_hour: float
    avg_per_day: float
    hourly_chart: list[ApiUsageChartPoint]
    daily_chart: list[ApiUsageChartPoint]
    operations_today: list[ApiUsageOperationRow]
    operations_period: list[ApiUsageOperationRow]


class AdminApiUsageOut(BaseModel):
    generated_at: str
    hours_window: int
    days_window: int
    sources: dict[str, ApiUsageSourceOut]


@router.get("/api-usage", response_model=AdminApiUsageOut)
async def admin_api_usage(
    hours: int = Query(24, ge=6, le=168),
    days: int = Query(7, ge=3, le=30),
    _: str = Depends(get_current_admin),
):
    from app.services.admin.api_usage import build_api_usage_report

    data = await build_api_usage_report(hours=hours, days=days)
    return AdminApiUsageOut(**data)


class TrafficChartPoint(BaseModel):
    label: str
    total: int
    unique: int = 0


class TrafficCountryRow(BaseModel):
    code: str
    name: str
    count: int
    share: float


class TrafficPageRow(BaseModel):
    path: str
    label: str
    count: int
    share: float


class TrafficHourRow(BaseModel):
    hour: int
    label: str
    count: int


class TrafficDeviceRow(BaseModel):
    device: str
    count: int


class TrafficCalendarDay(BaseModel):
    date: str
    label: str
    total: int
    unique: int
    selectable: bool
    is_future: bool


class AdminTrafficOut(BaseModel):
    generated_at: str
    hours_window: int
    days_window: int
    selected_date: str | None = None
    selected_day_total: int | None = None
    selected_day_unique: int | None = None
    online_now: int
    today_total: int
    today_unique: int
    last_hour_total: int
    period_total: int
    period_unique: int
    avg_per_day: float
    avg_per_hour: float
    hourly_chart: list[TrafficChartPoint]
    daily_chart: list[TrafficChartPoint]
    calendar: list[TrafficCalendarDay] = []
    calendar_month: str | None = None
    countries: list[TrafficCountryRow]
    top_pages: list[TrafficPageRow]
    time_of_day: list[TrafficHourRow]
    devices: list[TrafficDeviceRow]


@router.get("/traffic", response_model=AdminTrafficOut)
async def admin_traffic(
    hours: int = Query(24, ge=6, le=168),
    days: int = Query(7, ge=3, le=93),
    date: str | None = Query(None, description="YYYY-MM-DD — деталі за конкретний день"),
    month: str | None = Query(None, description="YYYY-MM — місяць календаря"),
    _: str = Depends(get_current_admin),
):
    from datetime import date as date_cls

    from app.services.admin.visit_stats import build_traffic_report

    focus_day = None
    if date:
        try:
            focus_day = date_cls.fromisoformat(date)
        except ValueError:
            focus_day = None

    data = await build_traffic_report(hours=hours, days=days, day=focus_day, month=month)
    return AdminTrafficOut(**data)
