"""AUTO.RIA live-пошук: HTML-картки/ID; деталі — HTML сторінка; фолбек на /auto/search."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from app.schemas.schemas import ListingOut, SearchFilters
from app.services.auto_ria.html_merge import listing_numeric_id
from app.services.auto_ria_beta.constants import PAGE_SIZE
from app.services.auto_ria_beta.errors import AutoRiaBetaError
from app.services.auto_ria_beta.service import fetch_auto_ria_beta_batch

logger = logging.getLogger(__name__)

HTML_DISCOVER_TIMEOUT_SECONDS = 25.0
HTML_FALLBACK_MESSAGE = "HTML-парсер AUTO.RIA недоступний."
_API_FALLBACK_SUFFIX = " Перемкнуто на API."


def _html_discover_error(message: str, *, allow_api_fallback: bool) -> str:
    if allow_api_fallback:
        return f"{message}{_API_FALLBACK_SUFFIX}"
    return message


@dataclass
class AutoRiaDiscoverResult:
    ids: list[str]
    cards: dict[str, ListingOut] = field(default_factory=dict)
    market_total: int = 0
    html_cursor: dict | None = None
    fallback: bool = False
    error: str | None = None


def cards_from_listings(listings: list[ListingOut]) -> tuple[list[str], dict[str, ListingOut]]:
    from app.services.listings.duplicates import mark_duplicates_in_pool

    listings = mark_duplicates_in_pool(list(listings))
    ids: list[str] = []
    cards: dict[str, ListingOut] = {}
    for listing in listings:
        aid = listing_numeric_id(listing)
        if not aid or aid in cards:
            continue
        cards[aid] = listing
        ids.append(aid)
    return ids, cards


async def _fallback_api(
    filters: SearchFilters,
    *,
    sort_by: str,
    max_ids: int,
    timeout: float,
    error: str,
) -> AutoRiaDiscoverResult:
    from app.services.auto_ria.service import collect_auto_ria_ids

    try:
        ids, total = await asyncio.wait_for(
            collect_auto_ria_ids(filters, max_ids=max_ids, sort_by=sort_by),
            timeout=timeout,
        )
    except Exception as exc:
        logger.warning("AUTO.RIA API fallback failed: %s", exc)
        return AutoRiaDiscoverResult(
            ids=[],
            market_total=0,
            fallback=True,
            error=f"{error} API також недоступний: {exc}",
        )
    return AutoRiaDiscoverResult(
        ids=list(ids),
        market_total=int(total or 0),
        fallback=True,
        error=error,
    )


async def discover_auto_ria(
    filters: SearchFilters,
    *,
    sort_by: str = "newest",
    start_page: int = 0,
    html_pages: int = 1,
    need: int = PAGE_SIZE,
    seen_ids: set[str] | None = None,
    html_timeout: float = HTML_DISCOVER_TIMEOUT_SECONDS,
    api_timeout: float = 90.0,
    api_max_ids: int = 2500,
    allow_api_fallback: bool = False,
) -> AutoRiaDiscoverResult:
    """Картки, count і ID — з HTML; API fallback лише якщо явно дозволено."""
    error: str | None = None
    batch = None
    try:
        batch = await asyncio.wait_for(
            fetch_auto_ria_beta_batch(
                filters,
                sort_by=sort_by,
                start_page=start_page,
                html_pages=html_pages,
                need=need,
                seen_ids=seen_ids,
            ),
            timeout=html_timeout,
        )
    except asyncio.TimeoutError:
        error = _html_discover_error(
            f"HTML-парсер: таймаут {html_timeout:.0f}s",
            allow_api_fallback=allow_api_fallback,
        )
    except AutoRiaBetaError as exc:
        error = _html_discover_error(
            f"HTML-парсер: {exc}",
            allow_api_fallback=allow_api_fallback,
        )
    except Exception as exc:
        logger.warning("AUTO.RIA HTML discover failed: %s", exc, exc_info=True)
        error = _html_discover_error(
            f"HTML-парсер: {exc}",
            allow_api_fallback=allow_api_fallback,
        )

    if batch is not None:
        if batch.error:
            error = _html_discover_error(
                f"HTML-парсер: {batch.error}",
                allow_api_fallback=allow_api_fallback,
            )
        elif start_page == 0 and not batch.listings and batch.market_total > 0:
            error = _html_discover_error(
                "HTML-парсер не розібрав картки",
                allow_api_fallback=allow_api_fallback,
            )

        if not error:
            ids, cards = cards_from_listings(list(batch.listings))
            return AutoRiaDiscoverResult(
                ids=ids,
                cards=cards,
                market_total=int(batch.market_total or 0),
                html_cursor={
                    "next_html_page": batch.next_html_page,
                    "exhausted": batch.exhausted,
                },
            )

    if allow_api_fallback and start_page == 0:
        return await _fallback_api(
            filters,
            sort_by=sort_by,
            max_ids=api_max_ids,
            timeout=api_timeout,
            error=error
            or _html_discover_error(HTML_FALLBACK_MESSAGE, allow_api_fallback=True),
        )

    return AutoRiaDiscoverResult(
        ids=[],
        market_total=0,
        html_cursor={"next_html_page": start_page, "exhausted": True},
        error=error,
        fallback=False,
    )
