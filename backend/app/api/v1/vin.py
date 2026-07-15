from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.schemas import VinCheckOut
from app.services.baza_gai.errors import BazaGaiError
from app.services.baza_gai.service import lookup_vin

router = APIRouter(prefix="/vin", tags=["vin"])


@router.get("/{vin}", response_model=VinCheckOut)
async def check_vin(
    vin: str,
    listing_id: str | None = Query(default=None),
    _user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> VinCheckOut:
    try:
        return await lookup_vin(vin, db=db, listing_id=listing_id)
    except BazaGaiError as exc:
        raise HTTPException(
            status_code=exc.status_code or 502,
            detail=str(exc),
        ) from exc
