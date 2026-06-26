from datetime import datetime, UTC, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_admin_token, get_current_admin
from app.models.models import User, SearchQuery, Notification, Favorite, PlanTier
from app.services.billing.plans import PLANS, get_plan

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminDashboardOut(BaseModel):
    total_users: int
    new_users_today: int
    new_users_week: int
    active_subscriptions: int
    trial_users: int
    telegram_connected: int
    total_searches: int
    total_notifications: int
    revenue_month_uah: int
    plan_breakdown: dict[str, int]
    registrations_chart: list[dict]


class AdminUserOut(BaseModel):
    id: str
    email: str
    name: str
    plan: str
    telegram_connected: bool
    telegram_username: str | None
    is_active: bool
    is_trial_active: bool
    searches_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserDetailOut(AdminUserOut):
    trial_ends_at: datetime | None
    plan_expires_at: datetime | None
    notifications_count: int
    favorites_count: int
    searches: list[dict]


class AdminUserUpdate(BaseModel):
    plan: str | None = None
    is_active: bool | None = None


class PaginatedUsers(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    per_page: int


class SubscriptionRow(BaseModel):
    plan: str
    plan_name: str
    count: int
    revenue_uah: int


class FinanceOut(BaseModel):
    mrr_uah: int
    arr_uah: int
    by_plan: list[SubscriptionRow]
    trial_count: int
    paid_count: int
    avg_revenue_per_user: float


@router.post("/auth/login", response_model=AdminTokenResponse)
async def admin_login(body: AdminLoginRequest):
    if body.username != settings.ADMIN_USERNAME or body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid credentials")
    return AdminTokenResponse(access_token=create_admin_token())


@router.get("/dashboard", response_model=AdminDashboardOut)
async def admin_dashboard(
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)

    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    new_today = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= today)
    ) or 0
    new_week = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= week_ago)
    ) or 0
    telegram_connected = await db.scalar(
        select(func.count()).select_from(User).where(User.telegram_connected.is_(True))
    ) or 0
    total_searches = await db.scalar(select(func.count()).select_from(SearchQuery)) or 0
    total_notifications = await db.scalar(select(func.count()).select_from(Notification)) or 0

    plan_breakdown: dict[str, int] = {}
    for tier in PlanTier:
        count = await db.scalar(
            select(func.count()).select_from(User).where(User.plan == tier)
        ) or 0
        plan_breakdown[tier.value] = count

    trial_users = 0
    users = await db.scalars(select(User))
    for u in users.all():
        if u.is_trial_active:
            trial_users += 1

    paid = sum(
        c for p, c in plan_breakdown.items() if p != "free"
    )
    revenue = sum(
        plan_breakdown.get(p, 0) * get_plan(p)["price_uah"]
        for p in plan_breakdown
    )

    chart = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        count = await db.scalar(
            select(func.count()).select_from(User).where(
                User.created_at >= day, User.created_at < next_day
            )
        ) or 0
        chart.append({"date": day.strftime("%d.%m"), "count": count})

    return AdminDashboardOut(
        total_users=total_users,
        new_users_today=new_today,
        new_users_week=new_week,
        active_subscriptions=paid,
        trial_users=trial_users,
        telegram_connected=telegram_connected,
        total_searches=total_searches,
        total_notifications=total_notifications,
        revenue_month_uah=revenue,
        plan_breakdown=plan_breakdown,
        registrations_chart=chart,
    )


@router.get("/users", response_model=PaginatedUsers)
async def admin_list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    plan: str | None = None,
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(User)
    if search:
        q = q.where(
            (User.email.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%"))
        )
    if plan:
        q = q.where(User.plan == plan)

    count_q = select(func.count()).select_from(User)
    if search:
        count_q = count_q.where(
            (User.email.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%"))
        )
    if plan:
        count_q = count_q.where(User.plan == plan)
    total = await db.scalar(count_q)
    result = await db.scalars(q.order_by(desc(User.created_at)).offset((page - 1) * per_page).limit(per_page))

    items = []
    for user in result.all():
        sc = await db.scalar(
            select(func.count()).select_from(SearchQuery).where(SearchQuery.user_id == user.id)
        ) or 0
        items.append(AdminUserOut(
            id=user.id, email=user.email, name=user.name,
            plan=user.plan.value, telegram_connected=user.telegram_connected,
            telegram_username=user.telegram_username, is_active=user.is_active,
            is_trial_active=user.is_trial_active, searches_count=sc,
            created_at=user.created_at,
        ))

    return PaginatedUsers(items=items, total=total or 0, page=page, per_page=per_page)


@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
async def admin_user_detail(
    user_id: str,
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    searches = await db.scalars(
        select(SearchQuery).where(SearchQuery.user_id == user_id).order_by(desc(SearchQuery.created_at))
    )
    notif_count = await db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
    ) or 0
    fav_count = await db.scalar(
        select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)
    ) or 0
    sc = await db.scalar(
        select(func.count()).select_from(SearchQuery).where(SearchQuery.user_id == user_id)
    ) or 0

    return AdminUserDetailOut(
        id=user.id, email=user.email, name=user.name,
        plan=user.plan.value, telegram_connected=user.telegram_connected,
        telegram_username=user.telegram_username, is_active=user.is_active,
        is_trial_active=user.is_trial_active, searches_count=sc,
        created_at=user.created_at,
        trial_ends_at=user.trial_ends_at,
        plan_expires_at=user.plan_expires_at,
        notifications_count=notif_count,
        favorites_count=fav_count,
        searches=[
            {"id": s.id, "name": s.name, "is_active": s.is_active,
             "new_count": s.new_count, "total_count": s.total_count}
            for s in searches.all()
        ],
    )


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def admin_update_user(
    user_id: str,
    body: AdminUserUpdate,
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    if body.plan is not None:
        try:
            user.plan = PlanTier(body.plan)
            user.plan_expires_at = datetime.now(UTC) + timedelta(days=30)
        except ValueError:
            raise HTTPException(400, "Invalid plan")
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()
    sc = await db.scalar(
        select(func.count()).select_from(SearchQuery).where(SearchQuery.user_id == user.id)
    ) or 0
    return AdminUserOut(
        id=user.id, email=user.email, name=user.name,
        plan=user.plan.value, telegram_connected=user.telegram_connected,
        telegram_username=user.telegram_username, is_active=user.is_active,
        is_trial_active=user.is_trial_active, searches_count=sc,
        created_at=user.created_at,
    )


@router.get("/subscriptions", response_model=list[SubscriptionRow])
async def admin_subscriptions(
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = []
    for plan_id, plan in PLANS.items():
        count = await db.scalar(
            select(func.count()).select_from(User).where(User.plan == plan_id)
        ) or 0
        rows.append(SubscriptionRow(
            plan=plan_id,
            plan_name=plan["name"],
            count=count,
            revenue_uah=count * plan["price_uah"],
        ))
    return rows


@router.get("/finance", response_model=FinanceOut)
async def admin_finance(
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    by_plan = []
    mrr = 0
    paid = 0
    trial = 0

    for plan_id, plan in PLANS.items():
        count = await db.scalar(
            select(func.count()).select_from(User).where(User.plan == plan_id)
        ) or 0
        rev = count * plan["price_uah"]
        mrr += rev
        if plan_id != "free":
            paid += count
        by_plan.append(SubscriptionRow(
            plan=plan_id, plan_name=plan["name"], count=count, revenue_uah=rev,
        ))

    users = await db.scalars(select(User))
    for u in users.all():
        if u.is_trial_active:
            trial += 1

    total_users = await db.scalar(select(func.count()).select_from(User)) or 1

    return FinanceOut(
        mrr_uah=mrr,
        arr_uah=mrr * 12,
        by_plan=by_plan,
        trial_count=trial,
        paid_count=paid,
        avg_revenue_per_user=round(mrr / total_users, 2),
    )
