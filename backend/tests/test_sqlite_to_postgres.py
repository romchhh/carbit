"""SQLite → PostgreSQL startup import."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from app.core.sqlite_to_postgres import (
    MARKER_FILE,
    MigrationStatus,
    _normalize_row,
    migrate_sqlite_to_postgres,
    resolve_sqlite_source,
)


class SqliteToPostgresHelpersTests(unittest.TestCase):
    def test_resolve_sqlite_source_relative(self):
        path = resolve_sqlite_source("database/autoradar.db")
        self.assertTrue(str(path).endswith("database/autoradar.db"))

    def test_normalize_row_parses_json(self):
        row = {"filters": json.dumps({"brand": "BMW"})}
        out = _normalize_row(row, "search_queries")
        self.assertEqual(out["filters"], {"brand": "BMW"})

    def test_normalize_row_bool_from_int(self):
        row = {"is_active": 1}
        out = _normalize_row(row, "users")
        self.assertTrue(out["is_active"])

    def test_normalize_row_parses_datetime(self):
        from datetime import datetime

        row = {
            "plan_expires_at": "2027-04-14 17:08:48.874799",
            "created_at": "2026-08-07 15:22:12.304228",
        }
        out = _normalize_row(row, "users")
        self.assertIsInstance(out["plan_expires_at"], datetime)
        self.assertIsInstance(out["created_at"], datetime)
        self.assertIsNotNone(out["plan_expires_at"].tzinfo)
        self.assertIsNotNone(out["created_at"].tzinfo)


class SqliteToPostgresSkipTests(unittest.IsolatedAsyncioTestCase):
    async def test_skips_when_target_not_postgres(self):
        result = await migrate_sqlite_to_postgres(
            postgres_url="sqlite+aiosqlite:///database/test.db",
            sqlite_path=Path("/tmp/missing.db"),
        )
        self.assertEqual(result.status, MigrationStatus.SKIPPED)

    async def test_skips_when_source_missing(self):
        result = await migrate_sqlite_to_postgres(
            postgres_url="postgresql+asyncpg://carbit:carbit@localhost:5432/carbit",
            sqlite_path=Path("/tmp/definitely-missing-carbit-sqlite.db"),
        )
        self.assertEqual(result.status, MigrationStatus.SKIPPED)


@unittest.skipUnless(
    os.getenv("TEST_POSTGRES_URL"),
    "Set TEST_POSTGRES_URL=postgresql+asyncpg://... to run integration test",
)
class SqliteToPostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._marker_backup = MARKER_FILE.read_text(encoding="utf-8") if MARKER_FILE.exists() else None
        if MARKER_FILE.exists():
            MARKER_FILE.unlink()

    async def asyncTearDown(self):
        if MARKER_FILE.exists():
            MARKER_FILE.unlink()
        if self._marker_backup is not None:
            MARKER_FILE.write_text(self._marker_backup, encoding="utf-8")

    async def test_imports_user_row(self):
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        from app.core.database import Base

        postgres_url = os.environ["TEST_POSTGRES_URL"]
        with tempfile.TemporaryDirectory() as tmp:
            sqlite_path = Path(tmp) / "source.db"
            src_engine = create_async_engine(
                f"sqlite+aiosqlite:///{sqlite_path}",
                connect_args={"check_same_thread": False},
            )
            dst_engine = create_async_engine(postgres_url)

            async with src_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(
                    text(
                        "INSERT INTO users (id, email, name, plan, preferred_currency, "
                        "telegram_connected, onboarding_completed, is_active, created_at, "
                        "plan_expires_at, trial_ends_at, phone_verified_at) "
                        "VALUES ('u1', 'test@example.com', 'Test', 'free', 'USD', 0, 0, 1, "
                        "'2026-08-07 15:22:12.304228', "
                        "'2027-04-14 17:08:48.874799', "
                        "'2026-08-10 15:22:12.300767', "
                        "'2026-08-07 15:22:12.300629')"
                    )
                )

            async with dst_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)

            try:
                result = await migrate_sqlite_to_postgres(
                    postgres_url=postgres_url,
                    sqlite_path=sqlite_path,
                    force=True,
                )
                self.assertEqual(result.status, MigrationStatus.IMPORTED)
                self.assertGreaterEqual(result.stats.get("users", 0), 1)

                async with dst_engine.connect() as conn:
                    count = await conn.scalar(text("SELECT COUNT(*) FROM users"))
                    self.assertEqual(int(count or 0), 1)
            finally:
                await src_engine.dispose()
                await dst_engine.dispose()


if __name__ == "__main__":
    unittest.main()
