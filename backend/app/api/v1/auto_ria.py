from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user_id
from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.auto_ria.search_endpoint import run_auto_ria_search

router = APIRouter(prefix="/auto-ria", tags=["auto-ria"])


@router.post("/search", response_model=PaginatedListings)
async def search_used_cars(
    filters: SearchFilters,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    sort_by: str = Query("price_asc"),
    mode: str = Query("preview", pattern="^(preview|browse)$"),
    user_id: str = Depends(get_current_user_id),
):
    return await run_auto_ria_search(
        filters,
        user_id=user_id,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        mode=mode,
    )
