"""Revision ID: 009_billing_failed_charges
Revises: 008
Create Date: 2026-07-14

billing_subscriptions раніше могла з’явитися лише через schema_ensure
(після старту uvicorn). Entrypoint ганяє alembic раніше — тому на свіжій
прод-БД таблиці ще немає. Ця ревізія створює таблицю або додає колонку.
"""

from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(
            sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:table"),
            {"table": table},
        ).fetchall()
        return bool(rows)
    rows = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :table"
        ),
        {"table": table},
    ).fetchall()
    return bool(rows)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
        return any(row[1] == column for row in rows)
    rows = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    ).fetchall()
    return bool(rows)


def _create_billing_subscriptions() -> None:
    op.create_table(
        "billing_subscriptions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="UAH"),
        sa.Column("periodicity", sa.String(), nullable=False, server_default="month"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("card_token", sa.String(), nullable=True),
        sa.Column("liqpay_payment_id", sa.String(), nullable=True),
        sa.Column("last_status", sa.String(), nullable=True),
        sa.Column("failed_charges", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_billing_subscriptions_order_id", "billing_subscriptions", ["order_id"])
    op.create_index("ix_billing_subscriptions_user_id", "billing_subscriptions", ["user_id"])


def upgrade() -> None:
    if not _has_table("billing_subscriptions"):
        _create_billing_subscriptions()
        return
    if not _has_column("billing_subscriptions", "failed_charges"):
        op.add_column(
            "billing_subscriptions",
            sa.Column("failed_charges", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    # Не дропаємо всю таблицю — могла з’явитися раніше з підписками.
    if _has_column("billing_subscriptions", "failed_charges"):
        op.drop_column("billing_subscriptions", "failed_charges")
