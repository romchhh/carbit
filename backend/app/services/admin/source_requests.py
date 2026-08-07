"""Адмінські операції з заявками на нові джерела."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import now_kyiv
from app.models.models import MonitoringSourceRequest, SourceRequestStatus, User
from app.schemas.schemas import AdminMonitoringSourceRequestOut


def _admin_out(row: MonitoringSourceRequest, user: User) -> AdminMonitoringSourceRequestOut:
    return AdminMonitoringSourceRequestOut(
        id=row.id,
        url=row.url,
        comment=row.comment,
        status=row.status.value,
        created_at=row.created_at,
        updated_at=row.updated_at,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        admin_note=row.admin_note,
    )


async def list_source_requests(
    db: AsyncSession,
    *,
    page: int,
    per_page: int,
    status: str | None,
    search: str,
) -> tuple[list[AdminMonitoringSourceRequestOut], int]:
    q = (
        select(MonitoringSourceRequest, User)
        .join(User, User.id == MonitoringSourceRequest.user_id)
    )
    count_q = select(func.count()).select_from(MonitoringSourceRequest).join(
        User, User.id == MonitoringSourceRequest.user_id
    )

    if status:
        try:
            st = SourceRequestStatus(status)
        except ValueError:
            st = None
        if st:
            q = q.where(MonitoringSourceRequest.status == st)
            count_q = count_q.where(MonitoringSourceRequest.status == st)

    if search.strip():
        term = f"%{search.strip()}%"
        filt = or_(
            MonitoringSourceRequest.url.ilike(term),
            MonitoringSourceRequest.comment.ilike(term),
            User.email.ilike(term),
            User.name.ilike(term),
        )
        q = q.where(filt)
        count_q = count_q.where(filt)

    total = await db.scalar(count_q) or 0
    rows = await db.execute(
        q.order_by(MonitoringSourceRequest.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = [_admin_out(row, user) for row, user in rows.all()]
    return items, int(total)


async def update_source_request(
    db: AsyncSession,
    request_id: str,
    *,
    status: str | None,
    admin_note: str | None,
) -> AdminMonitoringSourceRequestOut | None:
    row = await db.get(MonitoringSourceRequest, request_id)
    if not row:
        return None
    user = await db.get(User, row.user_id)
    if not user:
        return None

    if status:
        row.status = SourceRequestStatus(status)
    if admin_note is not None:
        row.admin_note = admin_note.strip() or None
    row.updated_at = now_kyiv()
    await db.commit()
    await db.refresh(row)
    return _admin_out(row, user)
