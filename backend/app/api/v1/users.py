from datetime import datetime, UTC, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import User, SearchQuery, Favorite, Notification
from app.schemas.schemas import DashboardStats, UserOut, OnboardingCompleteRequest
from app.schemas.user import user_out
from app.services.notifications.service import get_unread_count
from app.services.billing.plans import get_plan

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/me/onboarding", response_model=UserOut)
async def complete_onboarding(
    body: OnboardingCompleteRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.onboarding_completed = body.completed
    await db.flush()
    return user_out(user)


@router.get("/me/dashboard", response_model=DashboardStats)
async def dashboard_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    active_searches = await db.scalar(
        select(func.count()).select_from(SearchQuery).where(
            SearchQuery.user_id == user_id, SearchQuery.is_active.is_(True)
        )
    ) or 0

    favorites_count = await db.scalar(
        select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)
    ) or 0

    unread = await get_unread_count(db, user_id)

    new_today = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.created_at >= today_start,
        )
    ) or 0

    new_yesterday = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.created_at >= yesterday_start,
            Notification.created_at < today_start,
        )
    ) or 0

    return DashboardStats(
        active_searches=active_searches,
        searches_limit=user.searches_limit,
        new_listings_today=new_today,
        new_listings_yesterday=new_yesterday,
        favorites_count=favorites_count,
        unread_notifications=unread,
        plan=user.plan.value,
        is_trial_active=user.is_trial_active,
    )
