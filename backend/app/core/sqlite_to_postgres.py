"""One-time import of data from legacy SQLite autoradar.db into PostgreSQL."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import ROOT_DIR, settings

logger = logging.getLogger(__name__)

MARKER_FILE = ROOT_DIR / "database" / ".postgres_imported_from_sqlite"

def _import_marker_done() -> bool:
    if not MARKER_FILE.exists():
        return False
    try:
        first_line = MARKER_FILE.read_text(encoding="utf-8").splitlines()[0].strip()
    except OSError:
        return False
    return first_line.startswith("imported:")

# FK order: parents before children.
MIGRATION_TABLES: tuple[str, ...] = (
    "users",
    "parse_runs",
    "listings",
    "telegram_channels",
    "search_queries",
    "billing_subscriptions",
    "monitoring_source_requests",
    "saved_comparisons",
    "search_listings",
    "favorites",
    "notifications",
    "billing_payments",
)

JSON_COLUMNS: dict[str, frozenset[str]] = {
    "search_queries": frozenset({"filters"}),
    "parse_runs": frozenset({"log"}),
    "listings": frozenset({"images", "price_history"}),
    "notifications": frozenset({"payload"}),
    "saved_comparisons": frozenset({"listing_ids"}),
}

BATCH_SIZE = 200


def _is_postgres_url(url: str) -> bool:
    return url.startswith("postgresql") or url.startswith("postgres+")


def resolve_sqlite_source(path: str) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return (ROOT_DIR / raw).resolve()


def _normalize_value(column: str, value: object, table: str) -> object:
    if value is None:
        return None
    if column in JSON_COLUMNS.get(table, frozenset()) and isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    if isinstance(value, int) and column in {
        "is_active",
        "onboarding_completed",
        "telegram_connected",
        "is_duplicate",
        "is_new",
        "is_read",
        "sent_telegram",
        "enabled",
    }:
        return bool(value)
    return value


def _normalize_row(row: dict, table: str) -> dict:
    return {key: _normalize_value(key, value, table) for key, value in row.items()}


async def _table_exists(engine: AsyncEngine, table: str) -> bool:
    async with engine.connect() as conn:
        if engine.dialect.name == "sqlite":
            result = await conn.execute(
                text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": table},
            )
        else:
            result = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = :name"
                ),
                {"name": table},
            )
        return result.scalar() is not None


async def _row_count(engine: AsyncEngine, table: str) -> int:
    if not await _table_exists(engine, table):
        return 0
    async with engine.connect() as conn:
        result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        return int(result.scalar() or 0)


async def _copy_table(
    src: AsyncEngine,
    dst: AsyncEngine,
    table: str,
    *,
    skip_duplicate_of: bool = False,
) -> int:
    if not await _table_exists(src, table):
        return 0
    if not await _table_exists(dst, table):
        logger.warning("Skip %s: table missing in PostgreSQL (run alembic upgrade head)", table)
        return 0

    async with src.connect() as src_conn:
        result = await src_conn.execute(text(f"SELECT * FROM {table}"))
        rows = [dict(row) for row in result.mappings().all()]

    if not rows:
        return 0

    columns = list(rows[0].keys())
    if skip_duplicate_of and "duplicate_of" in columns:
        columns = [c for c in columns if c != "duplicate_of"]

    cols_sql = ", ".join(columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    stmt = text(
        f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders}) "
        "ON CONFLICT DO NOTHING"
    )

    copied = 0
    async with dst.begin() as dst_conn:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            for raw in batch:
                row = _normalize_row(raw, table)
                params = {c: row.get(c) for c in columns}
                await dst_conn.execute(stmt, params)
                copied += 1
    return copied


async def _apply_listing_duplicate_of(src: AsyncEngine, dst: AsyncEngine) -> int:
    if not await _table_exists(src, "listings"):
        return 0

    async with src.connect() as src_conn:
        result = await src_conn.execute(
            text("SELECT id, duplicate_of FROM listings WHERE duplicate_of IS NOT NULL")
        )
        pairs = [(row["id"], row["duplicate_of"]) for row in result.mappings().all()]

    if not pairs:
        return 0

    updated = 0
    async with dst.begin() as dst_conn:
        for listing_id, duplicate_of in pairs:
            res = await dst_conn.execute(
                text(
                    "UPDATE listings SET duplicate_of = :duplicate_of "
                    "WHERE id = :id AND duplicate_of IS NULL"
                ),
                {"id": listing_id, "duplicate_of": duplicate_of},
            )
            updated += res.rowcount or 0
    return updated


async def migrate_sqlite_to_postgres(
    *,
    postgres_url: str | None = None,
    sqlite_path: Path | None = None,
    force: bool = False,
) -> dict[str, int]:
    """Copy rows from SQLite autoradar.db into PostgreSQL. Idempotent (ON CONFLICT DO NOTHING)."""
    target_url = postgres_url or settings.DATABASE_URL
    if not _is_postgres_url(target_url):
        return {}

    source_path = sqlite_path or resolve_sqlite_source(settings.SQLITE_MIGRATE_SOURCE)
    if not source_path.is_file():
        logger.info("SQLite import skipped: source file not found (%s)", source_path)
        return {}

    if _import_marker_done() and not force:
        logger.info("SQLite import skipped: already completed (%s)", MARKER_FILE)
        return {}

    src_url = f"sqlite+aiosqlite:///{source_path}"
    src_engine = create_async_engine(src_url, connect_args={"check_same_thread": False})
    dst_engine = create_async_engine(target_url)

    try:
        src_users = await _row_count(src_engine, "users")
        if src_users == 0:
            logger.info("SQLite import skipped: source database is empty")
            return {}

        dst_users = await _row_count(dst_engine, "users")
        if dst_users > 0 and not force:
            logger.info(
                "SQLite import skipped: PostgreSQL already has %s users (set SQLITE_MIGRATE_FORCE=1 to merge)",
                dst_users,
            )
            return {}

        stats: dict[str, int] = {}
        logger.info("Importing SQLite data from %s → PostgreSQL", source_path)

        async with dst_engine.connect() as conn:
            await conn.execute(text("SET session_replication_role = 'replica'"))
            await conn.commit()

        try:
            for table in MIGRATION_TABLES:
                skip_dup = table == "listings"
                count = await _copy_table(
                    src_engine,
                    dst_engine,
                    table,
                    skip_duplicate_of=skip_dup,
                )
                stats[table] = count
                if count:
                    logger.info("  %s: %s rows", table, count)

            dup_updates = await _apply_listing_duplicate_of(src_engine, dst_engine)
            if dup_updates:
                stats["listings_duplicate_of"] = dup_updates
                logger.info("  listings.duplicate_of: %s updates", dup_updates)
        finally:
            async with dst_engine.connect() as conn:
                await conn.execute(text("SET session_replication_role = 'origin'"))
                await conn.commit()

        MARKER_FILE.write_text(
            f"imported:{sum(stats.values())}\nsource:{source_path}\n",
            encoding="utf-8",
        )
        logger.info("SQLite → PostgreSQL import finished (%s rows total)", sum(stats.values()))
        return stats
    finally:
        await src_engine.dispose()
        await dst_engine.dispose()


async def run_startup_migration() -> None:
    if not settings.SQLITE_MIGRATE_ENABLED:
        return
    if not _is_postgres_url(settings.DATABASE_URL):
        return
    force = str(settings.SQLITE_MIGRATE_FORCE).lower() in {"1", "true", "yes"}
    try:
        await migrate_sqlite_to_postgres(force=force)
    except Exception:
        logger.exception("SQLite → PostgreSQL import failed")
