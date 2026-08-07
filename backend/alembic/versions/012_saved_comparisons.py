"""Revision ID: 012_saved_comparisons
Revises: 011
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa


revision = "012"
down_revision = "011"
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


def upgrade() -> None:
    if _has_table("saved_comparisons"):
        return
    op.create_table(
        "saved_comparisons",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("listing_ids", sa.JSON(), nullable=False),
        sa.Column("share_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_saved_comparisons_user_id", "saved_comparisons", ["user_id"])
    op.create_index("ix_saved_comparisons_share_id", "saved_comparisons", ["share_id"], unique=True)


def downgrade() -> None:
    if _has_table("saved_comparisons"):
        op.drop_table("saved_comparisons")
