from __future__ import annotations

from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.olx.errors import raise_olx_http
from app.services.olx.service import search_olx
from app.services.search.preview_search import run_preview_search


async def run_olx_search(
    filters: SearchFilters,
    *,
    user_id: str,
    page: int,
    per_page: int,
    sort_by: str,
    mode: str,
) -> PaginatedListings:
    return await run_preview_search(
        filters,
        user_id=user_id,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        mode=mode,
        search=search_olx,
        on_error=raise_olx_http,
    )
