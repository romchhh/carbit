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

            if "billing_subscriptions" not in tables:
                await conn.execute(
                    text(
                        """
                        CREATE TABLE billing_subscriptions (
                            id VARCHAR NOT NULL PRIMARY KEY,
                            order_id VARCHAR NOT NULL UNIQUE,
                            user_id VARCHAR NOT NULL,
                            plan VARCHAR NOT NULL,
                            amount INTEGER NOT NULL,
                            currency VARCHAR NOT NULL DEFAULT 'UAH',
                            periodicity VARCHAR NOT NULL DEFAULT 'month',
                            status VARCHAR NOT NULL DEFAULT 'pending',
                            card_token VARCHAR,
                            card_mask VARCHAR,
                            liqpay_payment_id VARCHAR,
                            last_status VARCHAR,
                            failed_charges INTEGER NOT NULL DEFAULT 0,
                            created_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL,
                            cancelled_at DATETIME,
                            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
                        )
                        """
                    )
                )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_billing_subscriptions_order_id "
                        "ON billing_subscriptions (order_id)"
                    )
                )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_billing_subscriptions_user_id "
                        "ON billing_subscriptions (user_id)"
                    )
                )
                logger.warning("Created missing billing_subscriptions table")
            else:
                billing_cols = {
                    row[1]
                    for row in (
                        await conn.execute(text("PRAGMA table_info(billing_subscriptions)"))
                    ).fetchall()
                }
                if "failed_charges" not in billing_cols:
                    await conn.execute(
                        text(
                            "ALTER TABLE billing_subscriptions ADD COLUMN "
                            "failed_charges INTEGER NOT NULL DEFAULT 0"
                        )
                    )
                    logger.warning("Added missing billing_subscriptions.failed_charges column")
                if "card_mask" not in billing_cols:
                    await conn.execute(
                        text("ALTER TABLE billing_subscriptions ADD COLUMN card_mask VARCHAR")
                    )
                    logger.warning("Added missing billing_subscriptions.card_mask column")

            if "billing_payments" not in tables:
                await conn.execute(
                    text(
                        """
                        CREATE TABLE billing_payments (
                            id VARCHAR NOT NULL PRIMARY KEY,
                            user_id VARCHAR NOT NULL,
                            subscription_id VARCHAR,
                            order_id VARCHAR NOT NULL,
                            plan VARCHAR NOT NULL,
                            amount INTEGER NOT NULL,
                            currency VARCHAR NOT NULL DEFAULT 'UAH',
                            status VARCHAR NOT NULL,
                            liqpay_payment_id VARCHAR,
                            card_mask VARCHAR,
                            description VARCHAR,
                            paid_at DATETIME NOT NULL,
                            created_at DATETIME NOT NULL,
                            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
                            FOREIGN KEY(subscription_id) REFERENCES billing_subscriptions (id)
                                ON DELETE SET NULL
                        )
                        """
                    )
                )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_billing_payments_user_id "
                        "ON billing_payments (user_id)"
                    )
                )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_billing_payments_order_id "
                        "ON billing_payments (order_id)"
                    )
                )
                logger.warning("Created missing billing_payments table")
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
        billing_exists = await conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'billing_subscriptions'
                """
            )
        )
        if billing_exists.first() is None:
            await conn.execute(
                text(
                    """
                    CREATE TABLE billing_subscriptions (
                        id VARCHAR PRIMARY KEY,
                        order_id VARCHAR NOT NULL UNIQUE,
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        plan VARCHAR NOT NULL,
                        amount INTEGER NOT NULL,
                        currency VARCHAR NOT NULL DEFAULT 'UAH',
                        periodicity VARCHAR NOT NULL DEFAULT 'month',
                        status VARCHAR NOT NULL DEFAULT 'pending',
                        card_token VARCHAR,
                        card_mask VARCHAR,
                        liqpay_payment_id VARCHAR,
                        last_status VARCHAR,
                        failed_charges INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL,
                        cancelled_at TIMESTAMPTZ
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_billing_subscriptions_order_id "
                    "ON billing_subscriptions (order_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_billing_subscriptions_user_id "
                    "ON billing_subscriptions (user_id)"
                )
            )
            logger.warning("Created missing billing_subscriptions table")

        billing_col = await conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'billing_subscriptions'
                  AND column_name = 'failed_charges'
                """
            )
        )
        if billing_col.first() is None:
            # Таблиця може ще не існувати на свіжій БД з CREATE вище — тоді колонка вже є.
            table_ok = await conn.execute(
                text(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'billing_subscriptions'
                    """
                )
            )
            if table_ok.first() is not None:
                await conn.execute(
                    text(
                        "ALTER TABLE billing_subscriptions "
                        "ADD COLUMN failed_charges INTEGER NOT NULL DEFAULT 0"
                    )
                )
                logger.warning("Added missing billing_subscriptions.failed_charges column")

        card_mask_col = await conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'billing_subscriptions'
                  AND column_name = 'card_mask'
                """
            )
        )
        if card_mask_col.first() is None:
            table_ok = await conn.execute(
                text(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'billing_subscriptions'
                    """
                )
            )
            if table_ok.first() is not None:
                await conn.execute(
                    text("ALTER TABLE billing_subscriptions ADD COLUMN card_mask VARCHAR")
                )
                logger.warning("Added missing billing_subscriptions.card_mask column")

        payments_exists = await conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'billing_payments'
                """
            )
        )
        if payments_exists.first() is None:
            await conn.execute(
                text(
                    """
                    CREATE TABLE billing_payments (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        subscription_id VARCHAR REFERENCES billing_subscriptions(id)
                            ON DELETE SET NULL,
                        order_id VARCHAR NOT NULL,
                        plan VARCHAR NOT NULL,
                        amount INTEGER NOT NULL,
                        currency VARCHAR NOT NULL DEFAULT 'UAH',
                        status VARCHAR NOT NULL,
                        liqpay_payment_id VARCHAR,
                        card_mask VARCHAR,
                        description VARCHAR,
                        paid_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_billing_payments_user_id "
                    "ON billing_payments (user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_billing_payments_order_id "
                    "ON billing_payments (order_id)"
                )
            )
            logger.warning("Created missing billing_payments table")
