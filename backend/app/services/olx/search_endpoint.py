from __future__ import annotations

from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.auto_ria.preview_limits import clamp_preview_request, consume_preview_quota, is_preview_mode
from app.services.olx.errors import OlxError, raise_olx_http
from app.services.olx.service import search_olx


async def run_olx_search(
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
        return await search_olx(filters, page=page, per_page=per_page, sort_by=sort_by)
    except OlxError as exc:
        raise_olx_http(exc)
