from datetime import datetime, UTC, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import User, SearchQuery, Favorite, Notification
from app.schemas.schemas import (
    DashboardStats,
    UserOut,
    OnboardingCompleteRequest,
    EmailBindSendRequest,
    EmailBindVerifyRequest,
    MessageResponse,
)
from app.schemas.user import user_out
from app.services.notifications.service import get_unread_count
from app.services.billing.plans import get_plan
from app.services import email_bind as email_bind_svc
from app.services.email import send_verification_code
from app.services.telegram.links import is_placeholder_email

logger = logging.getLogger(__name__)

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


@router.post("/me/email/send-code", response_model=MessageResponse)
async def send_email_bind_code(
    body: EmailBindSendRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    if not is_placeholder_email(user.email):
        raise HTTPException(400, "Email вже підтверджено")

    email = body.email.strip().lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(400, "Email already registered")

    if not await email_bind_svc.resend_allowed(user_id):
        raise HTTPException(429, "Зачекайте перед повторним надсиланням")

    code = await email_bind_svc.store_email_bind(user_id, email)
    try:
        await send_verification_code(email, user.name, code)
    except Exception:
        logger.exception("Failed to send email bind code to %s", email)
        raise HTTPException(503, "Не вдалося надіслати код")

    return MessageResponse(message="Код підтвердження надіслано на email", expires_in=600)


@router.post("/me/email/verify", response_model=UserOut)
async def verify_email_bind(
    body: EmailBindVerifyRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    if not is_placeholder_email(user.email):
        raise HTTPException(400, "Email вже підтверджено")

    email = body.email.strip().lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(400, "Email already registered")

    ok = await email_bind_svc.verify_email_bind(user_id, email, body.code)
    if not ok:
        raise HTTPException(400, "Невірний або прострочений код")

    user.email = email
    await db.flush()
    return user_out(user)
