from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Listing, Notification
from app.schemas.schemas import PaginatedNotifications, NotificationOut, NotificationStats
from app.services.notifications.service import (
    get_unread_count,
    list_user_notifications,
    mark_all_read,
    notification_to_out,
)
from app.services.demo.seed import seed_demo_listings

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=PaginatedNotifications)
async def list_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    sort_by: str = Query("newest"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    items, total, unread = await list_user_notifications(
        db,
        user_id,
        page=page,
        per_page=per_page,
        unread_only=unread_only,
        sort_by=sort_by,
    )
    return PaginatedNotifications(
        items=items,
        total=total,
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
    listing = await db.get(Listing, n.listing_id) if n.listing_id else None
    return notification_to_out(n, listing)


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
