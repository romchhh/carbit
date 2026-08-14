"""Перевірка VIN через Базу ДАІ (baza-gai.com.ua) + аукціонну історію (autohelperbot)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import User
from app.schemas.schemas import (
    VinCheckHistoryItemOut,
    VinCheckHistoryOut,
    VinCheckOut,
    VinQuotaStatusOut,
)
from app.services.baza_gai.errors import BazaGaiError
from app.services.baza_gai.service import lookup_vin_check
from app.services.billing.plans import enforce_plan_expiry
from app.services.vin_history import list_global_vin_history, list_user_vin_history, record_vin_check
from app.services.vin_quota import enforce_vin_check_quota, vin_quota_status

router = APIRouter(prefix="/vin", tags=["vin"])


async def _load_user(db: AsyncSession, user_id: str) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if enforce_plan_expiry(user):
        await db.flush()
    return user


@router.get("/quota", response_model=VinQuotaStatusOut)
async def get_vin_quota(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(db, user_id)
    status = await vin_quota_status(user)
    await db.commit()
    return VinQuotaStatusOut(**status)


@router.get("/history/me", response_model=VinCheckHistoryOut)
async def get_my_vin_history(
    limit: int = Query(20, ge=1, le=40),
    user_id: str = Depends(get_current_user_id),
):
    items = await list_user_vin_history(user_id, limit=limit)
    return VinCheckHistoryOut(items=[VinCheckHistoryItemOut(**row) for row in items])


@router.get("/history/recent", response_model=VinCheckHistoryOut)
async def get_recent_vin_history(
    limit: int = Query(20, ge=1, le=40),
    _user_id: str = Depends(get_current_user_id),
):
    items = await list_global_vin_history(limit=limit)
    return VinCheckHistoryOut(items=[VinCheckHistoryItemOut(**row) for row in items])


@router.get("/{vin}", response_model=VinCheckOut)
async def check_vin(
    vin: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(db, user_id)

    try:
        await enforce_vin_check_quota(user, vin)
    except HTTPException:
        await db.commit()
        raise

    try:
        result = await lookup_vin_check(vin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BazaGaiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    await record_vin_check(user_id, result)
    await db.commit()
    return result
