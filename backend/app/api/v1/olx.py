from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user_id
from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.olx.search_endpoint import run_olx_search

router = APIRouter(prefix="/olx", tags=["olx"])


@router.post("/search", response_model=PaginatedListings)
async def search_olx_listings(
    filters: SearchFilters,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    sort_by: str = Query("newest"),
    mode: str = Query("preview", pattern="^(preview|browse)$"),
    user_id: str = Depends(get_current_user_id),
):
    return await run_olx_search(
        filters,
        user_id=user_id,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        mode=mode,
    )
