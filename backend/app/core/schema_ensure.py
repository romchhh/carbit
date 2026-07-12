"""Легкі schema-ensure для SQLite/Postgres, якщо alembic ще не догнав."""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def ensure_runtime_schema(engine: AsyncEngine) -> None:
    """Додає критичні колонки/таблиці, якщо їх ще немає (ідемпотентно)."""
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "sqlite":
            cols = {
                row[1]
                for row in (await conn.execute(text("PRAGMA table_info(users)"))).fetchall()
            }
            if "preferred_currency" not in cols:
                await conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN preferred_currency VARCHAR "
                        "NOT NULL DEFAULT 'USD'"
                    )
                )
                logger.warning("Added missing users.preferred_currency column")

            tables = {
                row[0]
                for row in (
                    await conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                ).fetchall()
            }
            if "telegram_channels" not in tables:
                await conn.execute(
                    text(
                        """
                        CREATE TABLE telegram_channels (
                            id VARCHAR NOT NULL PRIMARY KEY,
                            username VARCHAR NOT NULL UNIQUE,
                            title VARCHAR,
                            enabled BOOLEAN NOT NULL DEFAULT 1,
                            sort_order INTEGER NOT NULL DEFAULT 0,
                            created_at DATETIME NOT NULL
                        )
                        """
                    )
                )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_telegram_channels_username "
                        "ON telegram_channels (username)"
                    )
                )
                logger.warning("Created missing telegram_channels table")

            listing_cols = {
                row[1]
                for row in (await conn.execute(text("PRAGMA table_info(listings)"))).fetchall()
            }
            if "vin" not in listing_cols:
                await conn.execute(text("ALTER TABLE listings ADD COLUMN vin VARCHAR"))
                await conn.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_listings_vin ON listings (vin)")
                )
                logger.warning("Added missing listings.vin column")
            if "refreshed_at" not in listing_cols:
                await conn.execute(text("ALTER TABLE listings ADD COLUMN refreshed_at DATETIME"))
                logger.warning("Added missing listings.refreshed_at column")
            return

        # Postgres / others
        exists = await conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'preferred_currency'
                """
            )
        )
        if exists.first() is None:
            await conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN preferred_currency VARCHAR "
                    "NOT NULL DEFAULT 'USD'"
                )
            )
            logger.warning("Added missing users.preferred_currency column")

        table_exists = await conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'telegram_channels'
                """
            )
        )
        if table_exists.first() is None:
            await conn.execute(
                text(
                    """
                    CREATE TABLE telegram_channels (
                        id VARCHAR PRIMARY KEY,
                        username VARCHAR NOT NULL UNIQUE,
                        title VARCHAR,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_telegram_channels_username "
                    "ON telegram_channels (username)"
                )
            )
            logger.warning("Created missing telegram_channels table")

        for column, ddl in (
            ("vin", "ALTER TABLE listings ADD COLUMN vin VARCHAR"),
            ("refreshed_at", "ALTER TABLE listings ADD COLUMN refreshed_at TIMESTAMPTZ"),
        ):
            col_exists = await conn.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'listings' AND column_name = :column
                    """
                ),
                {"column": column},
            )
            if col_exists.first() is None:
                await conn.execute(text(ddl))
                if column == "vin":
                    await conn.execute(
                        text("CREATE INDEX IF NOT EXISTS ix_listings_vin ON listings (vin)")
                    )
                logger.warning("Added missing listings.%s column", column)