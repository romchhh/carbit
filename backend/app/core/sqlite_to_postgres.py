"""One-time import of data from legacy SQLite autoradar.db into PostgreSQL."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import ROOT_DIR, settings
from app.core.timezone import as_kyiv

logger = logging.getLogger(__name__)

MARKER_FILE = ROOT_DIR / "database" / ".postgres_imported_from_sqlite"

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

BOOLEAN_COLUMNS = frozenset({
    "is_active",
    "onboarding_completed",
    "telegram_connected",
    "is_duplicate",
    "is_new",
    "is_read",
    "sent_telegram",
    "enabled",
})


class MigrationStatus(str, Enum):
    SKIPPED = "skipped"
    IMPORTED = "imported"
    FAILED = "failed"


@dataclass
class MigrationResult:
    status: MigrationStatus
    message: str
    stats: dict[str, int] = field(default_factory=dict)
    error: str | None = None

    def log(self) -> None:
        prefix = {
            MigrationStatus.SKIPPED: "SKIP",
            MigrationStatus.IMPORTED: "OK",
            MigrationStatus.FAILED: "FAIL",
        }[self.status]
        print(f"[sqlite→postgres] {prefix}: {self.message}", flush=True)
        for table, count in self.stats.items():
            if count:
                print(f"  {table}: {count}", flush=True)
        if self.error:
            print(f"  error: {self.error}", flush=True)


def _import_marker_done() -> bool:
    if not MARKER_FILE.exists():
        return False
    try:
        first_line = MARKER_FILE.read_text(encoding="utf-8").splitlines()[0].strip()
    except OSError:
        return False
    return first_line.startswith("imported:")


def _is_postgres_url(url: str) -> bool:
    return url.startswith("postgresql") or url.startswith("postgres+")


def resolve_sqlite_source(path: str) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return (ROOT_DIR / raw).resolve()


def _is_datetime_column(column: str) -> bool:
    return column.endswith("_at") or column in {"published_at", "paid_at"}


def _parse_datetime(value: str) -> datetime:
    text_value = value.strip()
    if text_value.endswith("Z"):
        text_value = f"{text_value[:-1]}+00:00"
    if " " in text_value and "T" not in text_value and "+" not in text_value:
        text_value = text_value.replace(" ", "T", 1)
    return as_kyiv(datetime.fromisoformat(text_value))


def _json_for_postgres(value: object) -> str | None:
    """PostgreSQL + asyncpg через raw SQL потребує JSON як рядок + CAST."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            return value
    return json.dumps(value, ensure_ascii=False)


def _normalize_value(column: str, value: object, table: str) -> object:
    if value is None:
        return None
    if column in JSON_COLUMNS.get(table, frozenset()):
        return _json_for_postgres(value)
    if column in BOOLEAN_COLUMNS and isinstance(value, int):
        return bool(value)
    if _is_datetime_column(column) and isinstance(value, str):
        return _parse_datetime(value)
    if isinstance(value, datetime):
        return as_kyiv(value)
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

    json_cols = JSON_COLUMNS.get(table, frozenset())
    cols_sql = ", ".join(columns)
    placeholders = ", ".join(
        f"CAST(:{c} AS JSON)" if c in json_cols else f":{c}"
        for c in columns
    )
    stmt = text(
        f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders}) "
        "ON CONFLICT DO NOTHING"
    )

    copied = 0
    async with dst.begin() as dst_conn:
        for raw in rows:
            row = _normalize_row(raw, table)
            params = {c: row.get(c) for c in columns}
            try:
                await dst_conn.execute(stmt, params)
            except Exception as exc:
                row_id = row.get("id", row.get("email", "?"))
                raise RuntimeError(f"{table} row {row_id!r}: {exc}") from exc
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


def _should_merge(
    *,
    src_users: int,
    dst_users: int,
    src_listings: int,
    dst_listings: int,
    force: bool,
) -> bool:
    if force:
        return True
    if dst_users == 0:
        return True
    if src_users > dst_users or src_listings > dst_listings:
        return True
    return False


async def migrate_sqlite_to_postgres(
    *,
    postgres_url: str | None = None,
    sqlite_path: Path | None = None,
    force: bool = False,
) -> MigrationResult:
    """Copy rows from SQLite autoradar.db into PostgreSQL. Idempotent (ON CONFLICT DO NOTHING)."""
    target_url = postgres_url or settings.DATABASE_URL
    if not _is_postgres_url(target_url):
        return MigrationResult(
            MigrationStatus.SKIPPED,
            f"DATABASE_URL is not PostgreSQL ({target_url!r})",
        )

    source_path = sqlite_path or resolve_sqlite_source(settings.SQLITE_MIGRATE_SOURCE)
    if not source_path.is_file():
        return MigrationResult(
            MigrationStatus.SKIPPED,
            f"SQLite file not found: {source_path}",
        )

    if _import_marker_done() and not force:
        return MigrationResult(
            MigrationStatus.SKIPPED,
            f"already imported ({MARKER_FILE})",
        )

    src_url = f"sqlite+aiosqlite:///{source_path}"
    src_engine = create_async_engine(src_url, connect_args={"check_same_thread": False})
    dst_engine = create_async_engine(target_url)

    try:
        src_users = await _row_count(src_engine, "users")
        src_listings = await _row_count(src_engine, "listings")
        if src_users == 0 and src_listings == 0:
            return MigrationResult(
                MigrationStatus.SKIPPED,
                f"SQLite is empty ({source_path})",
            )

        dst_users = await _row_count(dst_engine, "users")
        dst_listings = await _row_count(dst_engine, "listings")

        if not _should_merge(
            src_users=src_users,
            dst_users=dst_users,
            src_listings=src_listings,
            dst_listings=dst_listings,
            force=force,
        ):
            return MigrationResult(
                MigrationStatus.SKIPPED,
                (
                    f"PostgreSQL already has more data "
                    f"(users {dst_users} vs sqlite {src_users}, "
                    f"listings {dst_listings} vs sqlite {src_listings}). "
                    "Set SQLITE_MIGRATE_FORCE=1 to merge anyway."
                ),
            )

        merge_note = ""
        if dst_users > 0 or dst_listings > 0:
            merge_note = " (merge: sqlite has more rows than postgres)"

        print(
            f"[sqlite→postgres] Importing {source_path} → PostgreSQL{merge_note}",
            flush=True,
        )
        print(
            f"  sqlite: users={src_users}, listings={src_listings} | "
            f"postgres: users={dst_users}, listings={dst_listings}",
            flush=True,
        )

        stats: dict[str, int] = {}

        async with dst_engine.connect() as conn:
            await conn.execute(text("SET session_replication_role = 'replica'"))
            await conn.commit()

        try:
            for table in MIGRATION_TABLES:
                count = await _copy_table(
                    src_engine,
                    dst_engine,
                    table,
                    skip_duplicate_of=table == "listings",
                )
                stats[table] = count
                if count:
                    print(f"  {table}: {count} rows", flush=True)

            dup_updates = await _apply_listing_duplicate_of(src_engine, dst_engine)
            if dup_updates:
                stats["listings_duplicate_of"] = dup_updates
                print(f"  listings.duplicate_of: {dup_updates} updates", flush=True)
        except Exception as exc:
            return MigrationResult(
                MigrationStatus.FAILED,
                "import failed during table copy",
                stats=stats,
                error=str(exc),
            )
        finally:
            async with dst_engine.connect() as conn:
                await conn.execute(text("SET session_replication_role = 'origin'"))
                await conn.commit()

        total = sum(stats.values())
        MARKER_FILE.write_text(
            f"imported:{total}\nsource:{source_path}\n",
            encoding="utf-8",
        )
        return MigrationResult(
            MigrationStatus.IMPORTED,
            f"finished ({total} rows processed)",
            stats=stats,
        )
    finally:
        await src_engine.dispose()
        await dst_engine.dispose()


async def run_startup_migration(*, fail_on_error: bool = True) -> MigrationResult:
    if not settings.SQLITE_MIGRATE_ENABLED:
        result = MigrationResult(MigrationStatus.SKIPPED, "SQLITE_MIGRATE_ENABLED=0")
        result.log()
        return result

    if not _is_postgres_url(settings.DATABASE_URL):
        result = MigrationResult(MigrationStatus.SKIPPED, "not using PostgreSQL")
        result.log()
        return result

    force = settings.SQLITE_MIGRATE_FORCE
    try:
        result = await migrate_sqlite_to_postgres(force=force)
        result.log()
        if result.status == MigrationStatus.FAILED and fail_on_error:
            raise RuntimeError(result.error or result.message)
        return result
    except Exception as exc:
        result = MigrationResult(
            MigrationStatus.FAILED,
            "import crashed",
            error=str(exc),
        )
        result.log()
        logger.exception("SQLite → PostgreSQL import failed")
        if fail_on_error:
            raise
        return result


async def migration_status_report() -> None:
    """Діагностика для ручного запуску."""
    source_path = resolve_sqlite_source(settings.SQLITE_MIGRATE_SOURCE)
    print(f"DATABASE_URL={settings.DATABASE_URL}", flush=True)
    print(f"SQLITE_MIGRATE_SOURCE={source_path} (exists={source_path.is_file()})", flush=True)
    print(f"SQLITE_MIGRATE_ENABLED={settings.SQLITE_MIGRATE_ENABLED}", flush=True)
    print(f"SQLITE_MIGRATE_FORCE={settings.SQLITE_MIGRATE_FORCE}", flush=True)
    print(f"marker={MARKER_FILE} (done={_import_marker_done()})", flush=True)

    if source_path.is_file():
        src_engine = create_async_engine(
            f"sqlite+aiosqlite:///{source_path}",
            connect_args={"check_same_thread": False},
        )
        try:
            users = await _row_count(src_engine, "users")
            listings = await _row_count(src_engine, "listings")
            print(f"sqlite rows: users={users}, listings={listings}", flush=True)
        finally:
            await src_engine.dispose()

    if _is_postgres_url(settings.DATABASE_URL):
        dst_engine = create_async_engine(settings.DATABASE_URL)
        try:
            users = await _row_count(dst_engine, "users")
            listings = await _row_count(dst_engine, "listings")
            print(f"postgres rows: users={users}, listings={listings}", flush=True)
        finally:
            await dst_engine.dispose()
