"""Revision ID: 009_billing_failed_charges
Revises: 008
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
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
    if not _has_column("billing_subscriptions", "failed_charges"):
        op.add_column(
            "billing_subscriptions",
            sa.Column("failed_charges", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _has_column("billing_subscriptions", "failed_charges"):
        op.drop_column("billing_subscriptions", "failed_charges")
