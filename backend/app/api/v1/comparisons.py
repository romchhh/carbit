"""Збережені списки порівняння авто."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.timezone import now_kyiv
from app.models.models import SavedComparison
from app.schemas.schemas import (
    SavedComparisonCreate,
    SavedComparisonDetailOut,
    SavedComparisonOut,
    SavedComparisonShareOut,
)
from app.services.comparisons.resolve import resolve_listings_for_ids

router = APIRouter(prefix="/comparisons", tags=["comparisons"])

_MAX_LISTINGS = 4
_MAX_SAVED = 20


def _new_share_id() -> str:
    return secrets.token_urlsafe(12)[:16]


def _to_out(row: SavedComparison) -> SavedComparisonOut:
    ids = [str(x) for x in (row.listing_ids or [])][: _MAX_LISTINGS]
    return SavedComparisonOut(
        id=row.id,
        name=row.name,
        listing_ids=ids,
        share_id=row.share_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[SavedComparisonOut])
async def list_saved_comparisons(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.scalars(
        select(SavedComparison)
        .where(SavedComparison.user_id == user_id)
        .order_by(SavedComparison.updated_at.desc())
    )
    return [_to_out(r) for r in rows.all()]


@router.post("", response_model=SavedComparisonOut, status_code=201)
async def create_saved_comparison(
    body: SavedComparisonCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    listing_ids = [str(x).strip() for x in body.listing_ids if str(x).strip()][: _MAX_LISTINGS]
    if len(listing_ids) < 2:
        raise HTTPException(400, "Потрібно мінімум 2 авто для збереження")

    total = await db.scalar(
        select(func.count()).select_from(SavedComparison).where(SavedComparison.user_id == user_id)
    ) or 0
    if total >= _MAX_SAVED:
        raise HTTPException(429, "Забагато збережених порівнянь — видаліть старі")

    name = (body.name or "").strip() or f"Порівняння {now_kyiv().strftime('%d.%m')}"
    row = SavedComparison(
        user_id=user_id,
        name=name[:120],
        listing_ids=listing_ids,
        share_id=_new_share_id(),
        created_at=now_kyiv(),
        updated_at=now_kyiv(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_out(row)


@router.get("/share/{share_id}", response_model=SavedComparisonShareOut)
async def get_shared_comparison(
    share_id: str,
    db: AsyncSession = Depends(get_db),
):
    row = await db.scalar(
        select(SavedComparison).where(SavedComparison.share_id == share_id)
    )
    if not row:
        raise HTTPException(404, "Порівняння не знайдено")
    listings = await resolve_listings_for_ids(db, [str(x) for x in row.listing_ids or []])
    return SavedComparisonShareOut(
        name=row.name,
        listing_ids=[str(x) for x in row.listing_ids or []],
        share_id=row.share_id,
        listings=listings,
    )


@router.get("/{comparison_id}", response_model=SavedComparisonDetailOut)
async def get_saved_comparison(
    comparison_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(SavedComparison, comparison_id)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "Порівняння не знайдено")
    listings = await resolve_listings_for_ids(db, [str(x) for x in row.listing_ids or []])
    return SavedComparisonDetailOut(
        **_to_out(row).model_dump(),
        listings=listings,
    )


@router.delete("/{comparison_id}", status_code=204)
async def delete_saved_comparison(
    comparison_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(SavedComparison, comparison_id)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "Порівняння не знайдено")
    await db.delete(row)
    await db.commit()
