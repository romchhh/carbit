"""Revision ID: 010_billing_payments
Revises: 009
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
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
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :table"),
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


def upgrade() -> None:
    if _has_table("billing_subscriptions") and not _has_column("billing_subscriptions", "card_mask"):
        op.add_column("billing_subscriptions", sa.Column("card_mask", sa.String(), nullable=True))

    if not _has_table("billing_payments"):
        op.create_table(
            "billing_payments",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("subscription_id", sa.String(), nullable=True),
            sa.Column("order_id", sa.String(), nullable=False),
            sa.Column("plan", sa.String(), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(), nullable=False, server_default="UAH"),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("liqpay_payment_id", sa.String(), nullable=True),
            sa.Column("card_mask", sa.String(), nullable=True),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["subscription_id"], ["billing_subscriptions.id"], ondelete="SET NULL"
            ),
        )
        op.create_index("ix_billing_payments_user_id", "billing_payments", ["user_id"])
        op.create_index("ix_billing_payments_order_id", "billing_payments", ["order_id"])
        op.create_index("ix_billing_payments_subscription_id", "billing_payments", ["subscription_id"])


def downgrade() -> None:
    if _has_table("billing_payments"):
        op.drop_table("billing_payments")
    if _has_column("billing_subscriptions", "card_mask"):
        op.drop_column("billing_subscriptions", "card_mask")
