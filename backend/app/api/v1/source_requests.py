"""Заявки користувачів на додавання каналів / сайтів для моніторингу."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.timezone import now_kyiv
from app.models.models import MonitoringSourceRequest, SourceRequestStatus, User
from app.schemas.schemas import MonitoringSourceRequestCreate, MonitoringSourceRequestOut

router = APIRouter(prefix="/source-requests", tags=["source-requests"])

_MAX_PENDING = 10
_URL_RE = re.compile(r"^https?://", re.I)


def _normalize_url(raw: str) -> str:
    url = raw.strip()
    if not url:
        raise HTTPException(400, "Вкажіть посилання")
    if url.startswith("@"):
        url = f"https://t.me/{url.lstrip('@')}"
    elif url.startswith("t.me/"):
        url = f"https://{url}"
    elif not _URL_RE.match(url):
        url = f"https://{url}"
    if len(url) > 2048:
        raise HTTPException(400, "Посилання занадто довге")
    return url


def _to_out(row: MonitoringSourceRequest) -> MonitoringSourceRequestOut:
    return MonitoringSourceRequestOut(
        id=row.id,
        url=row.url,
        comment=row.comment,
        status=row.status.value,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[MonitoringSourceRequestOut])
async def list_my_source_requests(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.scalars(
        select(MonitoringSourceRequest)
        .where(MonitoringSourceRequest.user_id == user_id)
        .order_by(MonitoringSourceRequest.created_at.desc())
    )
    return [_to_out(r) for r in rows.all()]


@router.post("", response_model=MonitoringSourceRequestOut, status_code=201)
async def create_source_request(
    body: MonitoringSourceRequestCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    pending = await db.scalar(
        select(func.count())
        .select_from(MonitoringSourceRequest)
        .where(
            MonitoringSourceRequest.user_id == user_id,
            MonitoringSourceRequest.status == SourceRequestStatus.pending,
        )
    ) or 0
    if pending >= _MAX_PENDING:
        raise HTTPException(
            429,
            "Забагато необроблених заявок. Дочекайтеся відповіді адміністратора.",
        )

    url = _normalize_url(body.url)
    comment = body.comment.strip() if body.comment else None

    row = MonitoringSourceRequest(
        user_id=user_id,
        url=url,
        comment=comment or None,
        status=SourceRequestStatus.pending,
        created_at=now_kyiv(),
        updated_at=now_kyiv(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_out(row)
