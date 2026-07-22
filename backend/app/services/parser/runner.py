from __future__ import annotations

import logging
from datetime import datetime

from app.core.timezone import format_kyiv, now_kyiv

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, ParseRun, ParseRunStatus, SearchQuery, User
from app.schemas.schemas import ListingOut
from app.services.listings.serialize import listing_to_out
from app.services.listings.upsert import upsert_listing
from app.services.parser.filter_groups import FilterGroup, filters_group_key, group_searches, parse_search_filters
from app.services.parser.linking import link_listing_to_search
from app.services.parser.settings import get_filter_cache, get_parser_settings, set_filter_cache
from app.services.notifications.freshness import coerce_notification_max_hours
from app.services.search.multi_source import normalize_sources, search_listings_outcome
from app.services.search.pool_cache import try_load_pool_listings
from app.services.telegram_channels.ingest import (
    mark_searches_checked,
    telegram_found_after_cutoff,
)
from app.services.telegram_channels.cycle import run_telegram_channels_cycle

logger = logging.getLogger(__name__)

UpsertedListing = tuple[ListingOut, Listing]


def _monitor_cache_ttl(settings: dict) -> int:
    interval = int(settings.get("interval_seconds") or 900)
    configured = int(settings.get("cache_ttl_seconds") or 1800)
    # Не довше половини інтервалу циклу і не більше 5 хв — достатньо для dedupe.
    return min(configured, max(60, interval // 2), 300)


def _sources_for_group(
    group: FilterGroup,
    searches: list[SearchQuery],
    *,
    sources_only: list[str] | None,
) -> list[str]:
    """Об'єднання джерел усіх пошуків групи — не тягнемо зайве AUTO.RIA/OLX/TG."""
    if sources_only:
        return normalize_sources(sources_only)

    union: set[str] = set()
    for search in searches:
        union.update(normalize_sources(parse_search_filters(search.filters).sources))

    if union:
        return sorted(union)
    return normalize_sources(group.filters.sources)


async def _link_listings_to_searches(
    db: AsyncSession,
    *,
    searches: list[SearchQuery],
    upserted: list[UpsertedListing],
    parse_sources: list[str],
    notify: bool,
    max_hours: float,
    log: list[str],
) -> tuple[int, int]:
    new_total = 0
    notifications = 0
    users_cache: dict[str, User | None] = {}
    notified_cars_in_batch: dict[str, list] = {}

    from app.services.listings.duplicates import listings_look_same

    def _batch_already_notified(user_id: str, listing) -> bool:
        for prev in notified_cars_in_batch.get(user_id, []):
            if listings_look_same(prev, listing):
                return True
        return False

    def _should_skip_notify_as_mirror(listing) -> bool:
        """Пропускаємо TG лише для дзеркала з тим самим VIN (не fuzzy brand/year)."""
        if not bool(getattr(listing, "is_duplicate", False)):
            return False
        parent_id = getattr(listing, "duplicate_of", None)
        if not parent_id:
            return False
        vin = (getattr(listing, "vin", None) or "").strip().upper()
        return len(vin) == 17

    for item, listing in upserted:
        for search in searches:
            search_sources = normalize_sources(parse_search_filters(search.filters).sources)
            if item.source not in search_sources:
                continue
            if search.user_id not in users_cache:
                users_cache[search.user_id] = await db.get(User, search.user_id)
            user = users_cache[search.user_id]

            do_notify = notify
            if do_notify and _should_skip_notify_as_mirror(listing):
                do_notify = False
            if do_notify and user and _batch_already_notified(user.id, listing):
                do_notify = False

            is_new, sent = await link_listing_to_search(
                db,
                search=search,
                listing_id=listing.id,
                notify=do_notify,
                user=user,
                max_notification_hours=max_hours,
            )
            if is_new:
                new_total += 1
            if sent and user:
                notified_cars_in_batch.setdefault(user.id, []).append(listing)
                notifications += 1

    return new_total, notifications


async def _process_group(
    db: AsyncSession,
    group: FilterGroup,
    *,
    max_listings: int,
    notify: bool,
    log: list[str],
    sources_only: list[str] | None = None,
) -> tuple[int, int, int]:
    """Returns found, new, notifications."""
    log.append(f"Група {group.key[:8]}… — {len(group.search_ids)} пошук(ів)" + (" [схожі]" if group.similar else ""))

    settings = await get_parser_settings()
    max_hours = coerce_notification_max_hours(settings.get("notification_max_published_hours", 1))
    max_hours_int = max(1, int(round(max_hours)))
    # Для виявлення нових оголошень шукаємо ширше, ніж вікно сповіщень.
    # Якщо авто з'являється як «нове» в UI — воно має прийти і в Telegram.
    discover_hours = max(max_hours_int, 6)
    notify_hours = float(discover_hours)  # вікно Telegram = вікно виявлення
    monitor_ttl = _monitor_cache_ttl(settings)

    searches: list[SearchQuery] = []
    for search_id in group.search_ids:
        search = await db.get(SearchQuery, search_id)
        if search and search.is_active:
            searches.append(search)

    parse_sources = _sources_for_group(group, searches, sources_only=sources_only)
    upserted: list[UpsertedListing] = []
    tg_found_after = (
        telegram_found_after_cutoff(searches, max_hours=discover_hours)
        if "telegram" in parse_sources
        else None
    )

    try:
        parse_filters = group.filters.model_copy(
            update={
                "sources": parse_sources,
                "published_within_hours": discover_hours,
            },
        )
        fetch_key = filters_group_key(parse_filters)

        # Короткий dedupe: нещодавно вже тягнули цю групу (on-demand + scheduler).
        # Для моніторингу — не ховаємося в кеш довше ніж половина monitor_ttl,
        # щоб нові авто не пропускати між циклами.
        cache_reuse_max = monitor_ttl // 2
        if not sources_only:
            cached = await get_filter_cache(fetch_key)
            if cached and cached.get("fetched_at"):
                try:
                    fetched_at = datetime.fromisoformat(str(cached["fetched_at"]))
                    age = (now_kyiv() - fetched_at).total_seconds()
                except (TypeError, ValueError):
                    age = cache_reuse_max + 1
                if age < cache_reuse_max:
                    log.append(f"  ⊘ Кеш {int(age)}s — пропуск API")
                    listing_ids = list(cached.get("listing_ids") or [])
                    upserted.clear()
                    for listing_id in listing_ids:
                        listing = await db.get(Listing, listing_id)
                        if not listing:
                            continue
                        upserted.append((listing_to_out(listing), listing))
                    new_total, notifications = await _link_listings_to_searches(
                        db,
                        searches=searches,
                        upserted=upserted,
                        parse_sources=parse_sources,
                        notify=notify,
                        max_hours=notify_hours,
                        log=log,
                    )
                    log.append(f"  ✓ З кешу: {len(upserted)} оголошень, нових {new_total}")
                    mark_searches_checked(searches)
                    return len(upserted), new_total, notifications

        # Live-pool: використовуємо якщо пул свіжий і не містить OLX/TG (AUTO.RIA-only).
        # Для OLX/TG — завжди йдемо в API: пул може не мати нових оголошень.
        has_olx_or_tg = bool({"olx", "telegram"} & set(parse_sources))
        pooled = await try_load_pool_listings(
            parse_filters,
            "published_desc",
            max_items=max_listings,
        )
        if pooled and not sources_only and not has_olx_or_tg:
            log.append(f"  ↺ Live-pool ({len(pooled)} огол.) — без зовнішніх API")
            upserted.clear()
            for item in pooled:
                listing = await upsert_listing(db, item)
                upserted.append((item, listing))
            listing_ids = [row.id for _, row in upserted]
            new_total, notifications = await _link_listings_to_searches(
                db,
                searches=searches,
                upserted=upserted,
                parse_sources=parse_sources,
                notify=notify,
                max_hours=notify_hours,
                log=log,
            )
            await set_filter_cache(fetch_key, listing_ids, ttl_seconds=settings["cache_ttl_seconds"])
            log.append(f"  ✓ З live-pool: {len(pooled)}, нових {new_total}")
            mark_searches_checked(searches)
            return len(pooled), new_total, notifications

        if tg_found_after is not None:
            log.append(f"  · Telegram DB: found_at > {format_kyiv(tg_found_after)}")

        outcome = await search_listings_outcome(
            parse_filters,
            page=1,
            per_page=max_listings,
            sort_by="published_desc",
            use_cache=True,
            cache_ttl_seconds=monitor_ttl,
            db=db,
            keyword_refresh=False,
            olx_enrich_details=False,
            telegram_found_after=tg_found_after,
        )
    except Exception as exc:
        log.append(f"  ✗ Помилка пошуку: {exc}")
        return 0, 0, 0

    log.append(f"  · Джерела: {', '.join(parse_sources)} · Telegram ≤ {max_hours_int} год")

    for status in outcome.sources:
        if status.error:
            log.append(f"  ⚠ {status.source}: {status.error}")
        else:
            log.append(f"  ✓ {status.source}: {status.item_count} оголошень")

    results = outcome.result
    found = len(results.items)
    listing_ids: list[str] = []

    upserted.clear()
    for item in results.items:
        listing = await upsert_listing(db, item)
        listing_ids.append(listing.id)
        upserted.append((item, listing))

    new_total, notifications = await _link_listings_to_searches(
        db,
        searches=searches,
        upserted=upserted,
        parse_sources=parse_sources,
        notify=notify,
        max_hours=notify_hours,
        log=log,
    )

    await set_filter_cache(
        fetch_key,
        listing_ids,
        ttl_seconds=settings["cache_ttl_seconds"],
    )
    olx_count = sum(1 for lid in listing_ids if lid.startswith("olx_"))
    auto_count = sum(1 for lid in listing_ids if lid.startswith("auto_ria_") or lid.startswith("new_auto_ria_"))
    tg_count = sum(1 for lid in listing_ids if lid.startswith("telegram_"))
    log.append(
        f"  ✓ Знайдено {found}, нових {new_total}, Telegram {notifications} "
        f"(AUTO.RIA {auto_count}, OLX {olx_count}, TG {tg_count})"
    )
    mark_searches_checked(searches)
    return found, new_total, notifications


async def run_parser_cycle(
    db: AsyncSession,
    *,
    triggered_by: str = "scheduler",
    sources: list[str] | None = None,
) -> ParseRun:
    """
    Запуск циклу парсингу.
    sources: None — усі джерела; інакше лише вказані (auto_ria, olx, telegram).
    """
    settings = await get_parser_settings()
    if not settings.get("enabled", True) and triggered_by == "scheduler":
        run = ParseRun(
            status=ParseRunStatus.success,
            triggered_by=triggered_by,
            log=["Парсинг вимкнено в налаштуваннях"],
            finished_at=now_kyiv(),
        )
        db.add(run)
        await db.flush()
        return run

    sources_only = None
    if sources:
        sources_only = normalize_sources(sources)

    run = ParseRun(status=ParseRunStatus.running, triggered_by=triggered_by, log=[])
    db.add(run)
    await db.flush()

    source_label = ", ".join(sources_only) if sources_only else "усі джерела"
    log: list[str] = [f"Старт {format_kyiv()} ({source_label})"]
    total_found = 0
    total_new = 0
    total_notifications = 0
    groups_count = 0
    searches_count = 0
    had_errors = False

    try:
        run_telegram = sources_only is None or "telegram" in sources_only
        if run_telegram and settings.get("telegram_enabled", True):
            try:
                tg_saved = await run_telegram_channels_cycle(db, settings, log)
                total_found += tg_saved
            except Exception as exc:
                had_errors = True
                log.append(f"Telegram ingest: {exc}")
                logger.exception("Telegram channels cycle failed")

        rows = await db.scalars(select(SearchQuery).where(SearchQuery.is_active.is_(True)))
        active = [(sq.id, sq.filters) for sq in rows.all()]
        searches_count = len(active)

        if not active:
            log.append("Немає активних пошуків")
        else:
            groups = group_searches(active, similar=True)
            groups_count = len(groups)
            similar_count = sum(1 for g in groups if g.similar)
            log.append(
                f"Активних пошуків: {searches_count}, груп fetch: {groups_count}"
                + (f" (схожих {similar_count})" if similar_count else "")
            )

            for group in groups:
                if sources_only == ["telegram"]:
                    group_sources = normalize_sources(group.filters.sources)
                    if "telegram" not in group_sources:
                        log.append(
                            f"  ⊘ Група {group.key[:8]}… — telegram не у джерелах пошуку"
                        )
                        continue
                try:
                    found, new, sent = await _process_group(
                        db,
                        group,
                        max_listings=settings["max_listings_per_group"],
                        notify=settings.get("notify_telegram", True),
                        log=log,
                        sources_only=sources_only,
                    )
                    total_found += found
                    total_new += new
                    total_notifications += sent
                except Exception as exc:
                    had_errors = True
                    log.append(f"  ✗ Група {group.key[:8]}…: {exc}")

        run.status = ParseRunStatus.partial if had_errors else ParseRunStatus.success
        run.filter_groups = groups_count
        run.searches_processed = searches_count
        run.listings_found = total_found
        run.listings_new = total_new
        run.notifications_sent = total_notifications
        run.log = log
        run.finished_at = now_kyiv()
        await db.flush()
        return run

    except Exception as exc:
        run.status = ParseRunStatus.failed
        run.error = str(exc)
        log.append(f"Критична помилка: {exc}")
        run.log = log
        run.finished_at = now_kyiv()
        await db.flush()
        raise


async def ingest_preview_results(
    db: AsyncSession,
    filters,
    items: list[ListingOut],
    *,
    total: int | None = None,
    pages: int | None = None,
) -> None:
    """Зберігає результати preview-пошуку в кеш і БД."""
    listing_ids: list[str] = []
    for item in items:
        listing = await upsert_listing(db, item)
        listing_ids.append(listing.id)

    key = filters_group_key(filters)
    settings = await get_parser_settings()
    await set_filter_cache(
        key,
        listing_ids,
        ttl_seconds=settings["cache_ttl_seconds"],
        total=total if total is not None else len(listing_ids),
        pages=pages,
    )


async def run_parser_for_search(db: AsyncSession, search_id: str) -> None:
    search = await db.get(SearchQuery, search_id)
    if not search or not search.is_active:
        return
    settings = await get_parser_settings()
    group = group_searches([(search.id, search.filters)])[0]
    log: list[str] = []
    await _process_group(
        db,
        group,
        max_listings=settings["max_listings_per_group"],
        notify=settings.get("notify_telegram", True),
        log=log,
    )
