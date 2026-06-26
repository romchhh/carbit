from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Notification
from app.schemas.schemas import PaginatedNotifications, NotificationOut, NotificationStats
from app.services.notifications.service import get_unread_count, mark_all_read
from app.services.demo.seed import seed_demo_listings

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=PaginatedNotifications)
async def list_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    base = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        base = base.where(Notification.is_read.is_(False))

    total = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            *( [Notification.is_read.is_(False)] if unread_only else [] ),
        )
    )
    unread = await get_unread_count(db, user_id)

    result = await db.scalars(
        base.order_by(Notification.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return PaginatedNotifications(
        items=result.all(),
        total=total or 0,
        unread=unread,
        page=page,
        per_page=per_page,
    )


@router.get("/stats", response_model=NotificationStats)
async def notification_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
    ) or 0
    unread = await get_unread_count(db, user_id)
    return NotificationStats(unread=unread, total=total)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    n = await db.get(Notification, notification_id)
    if not n or n.user_id != user_id:
        raise HTTPException(404, "Notification not found")
    n.is_read = True
    await db.flush()
    return n


@router.post("/read-all")
async def mark_all_notifications_read(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    count = await mark_all_read(db, user_id)
    return {"marked": count}


@router.post("/demo/seed")
async def seed_demo(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate demo listings + notifications (dev/demo without live API)."""
    result = await seed_demo_listings(db, user_id)
    return result
