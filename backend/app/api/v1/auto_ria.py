from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import get_current_user_id
from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.service import search_auto_ria

router = APIRouter(prefix="/auto-ria", tags=["auto-ria"])


@router.post("/search", response_model=PaginatedListings)
async def search_used_cars(
    filters: SearchFilters,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    sort_by: str = Query("price_asc"),
    _user_id: str = Depends(get_current_user_id),
):
    try:
        return await search_auto_ria(filters, page=page, per_page=per_page, sort_by=sort_by)
    except AutoRiaError as exc:
        status = exc.status_code or 502
        if "не налаштовано" in str(exc).lower():
            status = 503
        if "не знайдено" in str(exc).lower():
            status = 400
        raise HTTPException(status, str(exc)) from exc
