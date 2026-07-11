from __future__ import annotations

from app.core.config import settings as app_settings
from app.core.timezone import format_kyiv, now_kyiv

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ParseRun, ParseRunStatus, SearchQuery, User
from app.schemas.schemas import ListingOut
from app.services.listings.upsert import upsert_listing
from app.services.parser.filter_groups import FilterGroup, filters_group_key, group_searches, parse_search_filters
from app.services.parser.linking import link_listing_to_search
from app.services.parser.settings import get_parser_settings, set_filter_cache
from app.services.notifications.freshness import coerce_notification_max_hours
from app.services.search.multi_source import normalize_sources, search_listings_outcome


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
    log.append(f"Група {group.key[:8]}… — {len(group.search_ids)} пошук(ів)")

    settings = await get_parser_settings()
    max_hours = coerce_notification_max_hours(settings.get("notification_max_published_hours", 1))
    # Для SearchFilters потрібне int ≥ 1
    max_hours_int = max(1, int(round(max_hours)))

    try:
        parse_filters = group.filters.model_copy(
            update={"sources": normalize_sources(sources_only)}
        ) if sources_only else group.filters.model_copy(
            update={"sources": normalize_sources(group.filters.sources) or ["auto_ria", "olx"]}
        )
        if not sources_only:
            if "olx" not in parse_filters.sources:
                parse_filters = parse_filters.model_copy(
                    update={"sources": [*parse_filters.sources, "olx"]}
                )
            if "auto_ria" not in parse_filters.sources:
                parse_filters = parse_filters.model_copy(
                    update={"sources": ["auto_ria", *parse_filters.sources]}
                )
            if app_settings.TELEGRAM_ENABLED and "telegram" not in parse_filters.sources:
                parse_filters = parse_filters.model_copy(
                    update={"sources": [*parse_filters.sources, "telegram"]}
                )
        parse_filters = parse_filters.model_copy(
            update={"published_within_hours": max_hours_int},
        )

        outcome = await search_listings_outcome(
            parse_filters,
            page=1,
            per_page=max_listings,
            sort_by="published_desc",
            use_cache=False,
            db=db,
        )
    except Exception as exc:
        log.append(f"  ✗ Помилка пошуку: {exc}")
        return 0, 0, 0

    log.append(f"  · Telegram лише ≤ {max_hours_int} год від публікації")

    for status in outcome.sources:
        if status.error:
            log.append(f"  ⚠ {status.source}: {status.error}")
        else:
            log.append(f"  ✓ {status.source}: {status.item_count} оголошень")

    results = outcome.result
    found = len(results.items)
    new_total = 0
    notifications = 0
    listing_ids: list[str] = []

    searches = []
    for search_id in group.search_ids:
        search = await db.get(SearchQuery, search_id)
        if search and search.is_active:
            searches.append(search)

    users_cache: dict[str, User | None] = {}

    for item in results.items:
        listing = await upsert_listing(db, item)
        listing_ids.append(listing.id)

        for search in searches:
            search_sources = normalize_sources(parse_search_filters(search.filters).sources)
            if item.source not in search_sources:
                continue
            if search.user_id not in users_cache:
                users_cache[search.user_id] = await db.get(User, search.user_id)
            user = users_cache[search.user_id]
            is_new, sent = await link_listing_to_search(
                db,
                search=search,
                listing_id=listing.id,
                notify=notify,
                user=user,
                max_notification_hours=max_hours,
            )
            if is_new:
                new_total += 1
            if sent:
                notifications += 1

    await set_filter_cache(
        group.key,
        listing_ids,
        ttl_seconds=settings["cache_ttl_seconds"],
    )
    olx_count = sum(1 for lid in listing_ids if lid.startswith("olx_"))
    auto_count = sum(1 for lid in listing_ids if lid.startswith("auto_ria_"))
    tg_count = sum(1 for lid in listing_ids if lid.startswith("telegram_"))
    log.append(
        f"  ✓ Знайдено {found}, нових {new_total}, Telegram {notifications} "
        f"(AUTO.RIA {auto_count}, OLX {olx_count}, TG {tg_count})"
    )
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
        # Telethon history/live належить telegram_worker — не дублюємо сесію в parser cycle.
        run_telegram = sources_only is None or "telegram" in sources_only
        if run_telegram:
            log.append(
                "Telegram: ingest через telegram_worker (live + bootstrap); "
                "у циклі лише лінкування вже збережених оголошень"
            )

        rows = await db.scalars(select(SearchQuery).where(SearchQuery.is_active.is_(True)))
        active = [(sq.id, sq.filters) for sq in rows.all()]
        searches_count = len(active)

        if not active:
            log.append("Немає активних пошуків")
        else:
            groups = group_searches(active)
            groups_count = len(groups)
            log.append(f"Активних пошуків: {searches_count}, груп фільтрів: {groups_count}")

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
