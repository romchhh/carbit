"""seller contact columns on listings

Revision ID: 014
Revises: 013
Create Date: 2026-08-11
"""

from alembic import op
import sqlalchemy as sa


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
        return any(row[1] == column for row in rows)
    rows = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).fetchall()
    return bool(rows)


def upgrade() -> None:
    if not _has_column("listings", "seller_phone"):
        op.add_column("listings", sa.Column("seller_phone", sa.String(), nullable=True))
    if not _has_column("listings", "seller_telegram"):
        op.add_column("listings", sa.Column("seller_telegram", sa.String(), nullable=True))
    if not _has_column("listings", "seller_url"):
        op.add_column("listings", sa.Column("seller_url", sa.String(), nullable=True))


def downgrade() -> None:
    if _has_column("listings", "seller_url"):
        op.drop_column("listings", "seller_url")
    if _has_column("listings", "seller_telegram"):
        op.drop_column("listings", "seller_telegram")
    if _has_column("listings", "seller_phone"):
        op.drop_column("listings", "seller_phone")
