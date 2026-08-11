from __future__ import annotations

from datetime import datetime

from app.core.timezone import as_kyiv, now_kyiv

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, SearchListing, SearchQuery
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters, SearchQueryOut
from app.services.listings.serialize import listing_to_out
from app.services.parser.filter_groups import filters_group_key


def _first_image_url(images: object) -> str | None:
    if not isinstance(images, list):
        return None
    for item in images:
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None


async def preview_images_for_searches(
    db: AsyncSession,
    search_ids: list[str],
) -> dict[str, str]:
    """URL першого фото найновішого оголошення на кожний моніторинг."""
    if not search_ids:
        return {}
    rows = (
        await db.execute(
            select(SearchListing.search_id, Listing.images, Listing.published_at)
            .join(Listing, Listing.id == SearchListing.listing_id)
            .where(SearchListing.search_id.in_(search_ids))
            .order_by(Listing.published_at.desc())
        )
    ).all()
    previews: dict[str, str] = {}
    for search_id, images, _published in rows:
        if search_id in previews:
            continue
        url = _first_image_url(images)
        if url:
            previews[search_id] = url
    return previews


async def search_query_to_out(db: AsyncSession, search: SearchQuery) -> SearchQueryOut:
    previews = await preview_images_for_searches(db, [search.id])
    return SearchQueryOut.model_validate(search).model_copy(
        update={"preview_image": previews.get(search.id)}
    )


async def search_queries_to_out(
    db: AsyncSession,
    searches: list[SearchQuery],
) -> list[SearchQueryOut]:
    previews = await preview_images_for_searches(db, [s.id for s in searches])
    return [
        SearchQueryOut.model_validate(s).model_copy(
            update={"preview_image": previews.get(s.id)}
        )
        for s in searches
    ]


def _sort_items(
    items: list[tuple[ListingOut, datetime]],
    sort_by: str,
    *,
    prefer_new: bool = False,
) -> list[ListingOut]:
    from app.services.currency import listing_price_uah

    def new_rank(row: ListingOut) -> int:
        return 0 if prefer_new and row.is_new else 1

    if sort_by == "price_asc":
        ordered = sorted(
            items,
            key=lambda row: (new_rank(row[0]), listing_price_uah(row[0].price, row[0].currency)),
        )
        return [item for item, _ in ordered]
    if sort_by == "price_desc":
        ordered = sorted(
            items,
            key=lambda row: (
                new_rank(row[0]),
                -listing_price_uah(row[0].price, row[0].currency),
            ),
        )
        return [item for item, _ in ordered]
    if sort_by == "year_desc":
        ordered = sorted(items, key=lambda row: (new_rank(row[0]), -row[0].year))
        return [item for item, _ in ordered]
    if sort_by == "mileage_asc":
        ordered = sorted(items, key=lambda row: (new_rank(row[0]), row[0].mileage))
        return [item for item, _ in ordered]
    if sort_by in ("newest", "published_desc"):
        from app.services.listings.sort_dates import listing_sort_date

        ordered = sorted(
            items,
            key=lambda row: (new_rank(row[0]), -listing_sort_date(row[0]).timestamp()),
        )
        return [item for item, _ in ordered]
    ordered = sorted(items, key=lambda row: (new_rank(row[0]), -row[1].timestamp()))
    return [item for item, _ in ordered]


async def get_search_results_from_db(
    db: AsyncSession,
    search: SearchQuery,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    new_only: bool = False,
) -> PaginatedListings:
    stmt = (
        select(Listing, SearchListing)
        .join(SearchListing, SearchListing.listing_id == Listing.id)
        .where(SearchListing.search_id == search.id)
    )
    if new_only:
        stmt = stmt.where(SearchListing.is_new.is_(True))

    rows = (await db.execute(stmt)).all()
    paired = [
        (
            listing_to_out(listing).model_copy(update={"is_new": bool(sl.is_new)}),
            as_kyiv(listing.published_at),
        )
        for listing, sl in rows
    ]
    from app.services.listings.duplicates import collapse_listings_with_db_mirrors

    collapsed = await collapse_listings_with_db_mirrors(db, [item for item, _ in paired])
    pub_by_id = {item.id: pub for item, pub in paired}
    sorted_pairs: list[tuple[ListingOut, datetime]] = []
    for item in collapsed:
        pub = pub_by_id.get(item.id)
        if pub is None:
            for alt in item.alternate_sources or []:
                if alt.id and alt.id in pub_by_id:
                    pub = pub_by_id[alt.id]
                    break
        if pub is None:
            pub = as_kyiv(item.published_at)
        sorted_pairs.append((item, pub))
    items = _sort_items(sorted_pairs, sort_by, prefer_new=True)

    total = len(items)
    start = (page - 1) * per_page
    page_items = items[start : start + per_page]
    pages = (total + per_page - 1) // per_page if total else 0

    return PaginatedListings(
        items=page_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


async def get_cached_preview_results(
    db: AsyncSession,
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings | None:
    from app.services.parser.settings import get_filter_cache, get_parser_settings

    settings = await get_parser_settings()
    cache = await get_filter_cache(filters_group_key(filters))
    if not cache:
        return None

    fetched_at = cache.get("fetched_at")
    if not fetched_at:
        return None

    try:
        fetched = as_kyiv(datetime.fromisoformat(fetched_at))
    except ValueError:
        return None

    age = (now_kyiv() - fetched).total_seconds()
    if age > settings["cache_ttl_seconds"]:
        return None

    listing_ids = cache.get("listing_ids") or []
    if not listing_ids:
        return PaginatedListings(items=[], total=0, page=page, per_page=per_page, pages=0)

    result = await db.scalars(select(Listing).where(Listing.id.in_(listing_ids)))
    listings = {item.id: item for item in result.all()}
    paired = [
        (listing_to_out(listings[lid]), as_kyiv(listings[lid].published_at))
        for lid in listing_ids
        if lid in listings
    ]
    try:
        items = _sort_items(paired, sort_by)
    except Exception:
        items = [item for item, _ in paired]

    # Старий кеш без total ламав «Показати ще» (total == len(ids) ≈ 20).
    # Без збереженого total не використовуємо кеш — йдемо в живий пошук.
    cached_total = cache.get("total")
    if cached_total is None:
        return None

    try:
        total = int(cached_total)
    except (TypeError, ValueError):
        return None
    start = (page - 1) * per_page
    page_items = items[start : start + per_page]
    pages = int(cache["pages"]) if cache.get("pages") is not None else (
        (total + per_page - 1) // per_page if total else 0
    )

    return PaginatedListings(
        items=page_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


async def mark_search_listings_seen(db: AsyncSession, search: SearchQuery) -> int:
    rows = await db.scalars(
        select(SearchListing).where(
            SearchListing.search_id == search.id,
            SearchListing.is_new.is_(True),
        )
    )
    count = 0
    for row in rows.all():
        row.is_new = False
        count += 1
    search.new_count = 0
    await db.flush()
    return count
