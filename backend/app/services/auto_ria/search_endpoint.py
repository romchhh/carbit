from __future__ import annotations

from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.errors import raise_auto_ria_http
from app.services.auto_ria.preview_limits import clamp_preview_request, consume_preview_quota, is_preview_mode
from app.services.auto_ria.service import search_auto_ria


async def run_auto_ria_search(
    filters: SearchFilters,
    *,
    user_id: str,
    page: int,
    per_page: int,
    sort_by: str,
    mode: str,
) -> PaginatedListings:
    if is_preview_mode(mode):
        await consume_preview_quota(user_id)

    page, per_page = clamp_preview_request(page=page, per_page=per_page, mode=mode)

    try:
        return await search_auto_ria(filters, page=page, per_page=per_page, sort_by=sort_by)
    except AutoRiaError as exc:
        raise_auto_ria_http(exc)
