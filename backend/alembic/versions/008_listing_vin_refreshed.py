"""Revision ID: 008_listing_vin_refreshed
Revises: 007
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "008"
down_revision = "007"
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
    if not _has_column("listings", "vin"):
        op.add_column("listings", sa.Column("vin", sa.String(), nullable=True))
        op.create_index("ix_listings_vin", "listings", ["vin"])
    if not _has_column("listings", "refreshed_at"):
        op.add_column(
            "listings",
            sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if _has_column("listings", "refreshed_at"):
        op.drop_column("listings", "refreshed_at")
    if _has_column("listings", "vin"):
        op.drop_index("ix_listings_vin", table_name="listings")
        op.drop_column("listings", "vin")
