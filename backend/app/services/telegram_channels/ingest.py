from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import as_kyiv, now_kyiv
from app.models.models import Listing, SearchQuery, Source, User
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.mapper import sort_listings
from app.services.listings.serialize import listing_to_out
from app.services.listings.upsert import upsert_listing
from app.services.parser.filter_groups import parse_search_filters
from app.services.parser.linking import link_listing_to_search
from app.services.parser.settings import get_parser_settings
from app.services.notifications.freshness import coerce_notification_max_hours
from app.services.search.brand_model_keywords import (
    collect_brand_keyword_variants,
    collect_model_keyword_variants,
    filter_sql_search_tokens,
)
from app.services.telegram_channels.mapper import (
    car_listing_to_listing_out,
    listing_out_matches_filters,
    telegram_listing_id,
    telegram_text_is_search_request,
)

logger = logging.getLogger(__name__)


def telegram_found_after_cutoff(
    searches: list[SearchQuery],
    *,
    max_hours: int,
) -> datetime:
    """Для cron: лише оголошення з found_at новіші за last_checked_at групи."""
    if not searches:
        return now_kyiv() - timedelta(hours=max(1, max_hours))

    if any(search.last_checked_at is None for search in searches):
        return now_kyiv() - timedelta(hours=max(1, max_hours))

    return min(as_kyiv(search.last_checked_at) for search in searches if search.last_checked_at)


def mark_searches_checked(searches: list[SearchQuery]) -> None:
    """Оновлює last_checked_at після успішного проходу групи (watermark для TG)."""
    checked_at = now_kyiv()
    for search in searches:
        search.last_checked_at = checked_at


def _save_photo_refs_from_car(car_listing) -> str:
    """Зберігає refs для lazy download; повертає listing_id."""
    from app.services.telegram_channels.bootstrap import ensure_parser_path

    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    listing_id = telegram_listing_id(car_listing.channel, car_listing.message_id)
    ids = list(car_listing.group_message_ids or []) or [car_listing.message_id]
    ChannelMediaStore().save_photo_refs(listing_id, car_listing.channel, ids)
    return listing_id


async def ingest_telegram_listing(
    db: AsyncSession,
    car_listing,
    *,
    notify: bool = True,
    link_searches: bool = True,
    parser_service=None,
) -> tuple[ListingOut, int, int, bool]:
    """Upsert telegram listing and optionally link to matching active searches.

    Returns (item, new_links, notifications, matched_any_search).
    Якщо передано parser_service — одне фото завантажується до сповіщень у Telegram.
    """
    if telegram_text_is_search_request(getattr(car_listing, "raw_text", "") or ""):
        logger.debug(
            "Skip telegram ingest: search request (not a sale), channel=%s msg=%s",
            getattr(car_listing, "channel", ""),
            getattr(car_listing, "message_id", ""),
        )
        placeholder = car_listing_to_listing_out(car_listing)
        return placeholder, 0, 0, False

    item = car_listing_to_listing_out(car_listing)
    _save_photo_refs_from_car(car_listing)
    listing = await upsert_listing(db, item)

    if parser_service is not None:
        from app.services.telegram_channels.lazy_photos import attach_photos_to_listing

        urls = await attach_photos_to_listing(
            db,
            parser_service,
            listing.id,
            max_photos=1,
        )
        if urls:
            item = listing_to_out(listing)

    if not link_searches:
        return item, 0, 0, False

    parser_settings = await get_parser_settings()
    if not parser_settings.get("notify_telegram", True):
        notify = False
    max_hours = coerce_notification_max_hours(
        parser_settings.get("notification_max_published_hours", 6)
    )

    searches = await db.scalars(select(SearchQuery).where(SearchQuery.is_active.is_(True)))
    new_total = 0
    notifications = 0
    matched_any = False
    users_cache: dict[str, User | None] = {}

    for search in searches.all():
        filters = parse_search_filters(search.filters)
        sources = filters.sources
        if sources and "telegram" not in [s.lower() for s in sources]:
            continue
        if not listing_out_matches_filters(item, filters):
            continue

        matched_any = True
        if search.user_id not in users_cache:
            users_cache[search.user_id] = await db.get(User, search.user_id)
        user = users_cache[search.user_id]
        before_new = search.new_count or 0
        is_new, sent = await link_listing_to_search(
            db,
            search=search,
            listing_id=listing.id,
            notify=notify,
            user=user,
            max_notification_hours=max_hours,
        )
        if (search.new_count or 0) > before_new:
            new_total += 1
        if sent:
            notifications += 1

    if matched_any:
        from app.services.telegram_channels.bootstrap import ensure_parser_path

        ensure_parser_path()
        from parser.channel_media_store import ChannelMediaStore

        ChannelMediaStore().enqueue_photo_download(item.id)

    return item, new_total, notifications, matched_any


def _telegram_sql_prefilters(filters: SearchFilters, *, found_after: datetime | None = None):
    """Грубі SQL-предикати — менше рядків тягнемо в Python."""
    clauses = [Listing.source == Source.telegram]

    if found_after is not None:
        clauses.append(Listing.found_at > as_kyiv(found_after))

    brand = (filters.brand or "").strip()
    model_str = (filters.model or "").strip()
    if brand:
        brand_variants = filter_sql_search_tokens(collect_brand_keyword_variants(brand), limit=12)
        brand_clauses = []
        for variant in brand_variants:
            like = f"%{variant}%"
            brand_clauses.extend(
                [
                    Listing.brand.ilike(like),
                    Listing.title.ilike(like),
                    Listing.description.ilike(like),
                ]
            )
        # Якщо модель унікально ідентифікує бренд (Discovery → Land Rover),
        # старі listings можуть мати brand="Discovery" — додаємо перевірку в brand clause.
        if model_str:
            from app.services.search.brand_model_keywords import (
                _allows_distinctive_model_without_brand,
                collect_model_keyword_variants,
            )
            if _allows_distinctive_model_without_brand(brand, model_str):
                model_v = filter_sql_search_tokens(
                    collect_model_keyword_variants(brand, model_str), limit=6
                )
                for mv in model_v:
                    like = f"%{mv}%"
                    # description обовʼязково: при mis-parse brand=BMW title може не
                    # містити Countryman, а body — так.
                    brand_clauses.extend(
                        [
                            Listing.brand.ilike(like),
                            Listing.title.ilike(like),
                            Listing.description.ilike(like),
                            Listing.model.ilike(like),
                        ]
                    )
        if brand_clauses:
            clauses.append(or_(*brand_clauses))

    model = model_str  # використовуємо вже оголошений model_str
    if model:
        model_variants = filter_sql_search_tokens(
            collect_model_keyword_variants(filters.brand or "", model),
            limit=12,
        )
        if not model_variants:
            model_variants = (model,)
        model_clauses = []
        for variant in model_variants:
            like = f"%{variant}%"
            model_clauses.extend(
                [
                    Listing.model.ilike(like),
                    Listing.title.ilike(like),
                    Listing.description.ilike(like),
                ]
            )
        if model_clauses:
            clauses.append(or_(*model_clauses))

    if filters.year_from or filters.year_to:
        clauses.append(Listing.year > 0)
        if filters.year_from:
            clauses.append(Listing.year >= filters.year_from)
        if filters.year_to:
            clauses.append(Listing.year <= filters.year_to)

    if filters.mileage_from:
        clauses.append(
            or_(Listing.mileage == 0, Listing.mileage >= filters.mileage_from)
        )
    if filters.mileage_to:
        clauses.append(
            or_(Listing.mileage == 0, Listing.mileage <= filters.mileage_to)
        )

    return and_(*clauses)


async def _telegram_listings_matching_filters(
    db: AsyncSession,
    filters: SearchFilters,
    *,
    found_after: datetime | None,
    scan_limit: int,
) -> list[ListingOut]:
    order_col = Listing.found_at.desc() if found_after is not None else Listing.published_at.desc()
    rows = await db.scalars(
        select(Listing)
        .where(_telegram_sql_prefilters(filters, found_after=found_after))
        .order_by(order_col)
        .limit(scan_limit)
    )
    matched: list[ListingOut] = []
    from app.services.telegram_channels.lazy_photos import enqueue_listing_photos

    for listing in rows.all():
        item = listing_to_out(listing)
        if listing_out_matches_filters(item, filters):
            matched.append(item)
            if not (item.images or []):
                enqueue_listing_photos(item.id)
    from app.services.listings.duplicates import dedupe_telegram_posts_in_pool

    return dedupe_telegram_posts_in_pool(matched)


async def search_telegram_listings(
    db: AsyncSession,
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    max_scan: int = 3000,
    keyword_refresh: bool = True,
    found_after: datetime | None = None,
) -> PaginatedListings:
    if keyword_refresh:
        try:
            from app.services.telegram_channels.keyword_refresh import (
                refresh_telegram_by_keywords,
            )

            await refresh_telegram_by_keywords(filters)
        except Exception:
            logger.exception("Telegram keyword refresh failed")

    scan_limit = max_scan if found_after is None else min(max_scan, 3000)

    matched = await _telegram_listings_matching_filters(
        db,
        filters,
        found_after=found_after,
        scan_limit=scan_limit,
    )

    # Якщо в БД порожньо або замало матчів — Telethon search + history scan.
    from app.services.telegram_channels.keyword_refresh import (
        THIN_RESULT_RETRY_THRESHOLD,
        THIN_RETRY_WAIT_SECONDS,
        refresh_telegram_by_keywords,
    )

    thin = len(matched) < THIN_RESULT_RETRY_THRESHOLD
    if keyword_refresh and thin and ((filters.brand or "").strip() or (filters.model or "").strip()):
        try:
            await refresh_telegram_by_keywords(
                filters,
                wait_seconds=THIN_RETRY_WAIT_SECONDS,
                force_rescan=True,
                include_history_scan=True,
            )
            matched = await _telegram_listings_matching_filters(
                db,
                filters,
                found_after=found_after,
                scan_limit=scan_limit,
            )
        except Exception:
            logger.exception("Telegram keyword refresh retry failed")

    matched = sort_listings(matched, sort_by)
    total = len(matched)
    start = (page - 1) * per_page
    page_items = matched[start : start + per_page]
    pages = (total + per_page - 1) // per_page if total else 0

    return PaginatedListings(
        items=page_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
