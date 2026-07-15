"""Перевірка VIN через Базу ДАІ (baza-gai.com.ua)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user_id
from app.schemas.schemas import VinCheckOut
from app.services.baza_gai.errors import BazaGaiError
from app.services.baza_gai.service import lookup_vin_check

router = APIRouter(prefix="/vin", tags=["vin"])


@router.get("/{vin}", response_model=VinCheckOut)
async def check_vin(
    vin: str,
    _user_id: str = Depends(get_current_user_id),
):
    try:
        return await lookup_vin_check(vin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BazaGaiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
