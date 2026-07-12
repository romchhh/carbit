"""Revision ID: 005_preferred_currency
Revises: 004
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
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
    if _has_column("users", "preferred_currency"):
        return
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("preferred_currency", sa.String(), nullable=False, server_default="UAH")
        )


def downgrade() -> None:
    if not _has_column("users", "preferred_currency"):
        return
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("preferred_currency")
