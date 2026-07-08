from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.auto_ria.preview_limits import clamp_preview_request, consume_preview_quota, is_preview_mode


async def run_preview_search(
    filters: SearchFilters,
    *,
    user_id: str,
    page: int,
    per_page: int,
    sort_by: str,
    mode: str,
    search: Callable[..., Awaitable[PaginatedListings]],
    on_error: Callable[[Exception], None],
) -> PaginatedListings:
    """Спільна обгортка для preview-пошуку AUTO.RIA / OLX."""
    if is_preview_mode(mode) and page == 1:
        await consume_preview_quota(user_id)

    page, per_page = clamp_preview_request(page=page, per_page=per_page, mode=mode)

    try:
        return await search(filters, page=page, per_page=per_page, sort_by=sort_by)
    except Exception as exc:
        on_error(exc)
        raise  # unreachable if on_error raises
