"""Revision ID: 013_user_phone
Revises: 012
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa


revision = "013"
down_revision = "012"
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
    if not _has_column("users", "phone"):
        op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))
        op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    if not _has_column("users", "phone_verified_at"):
        op.add_column(
            "users",
            sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if _has_column("users", "phone_verified_at"):
        op.drop_column("users", "phone_verified_at")
    if _has_column("users", "phone"):
        op.drop_index("ix_users_phone", table_name="users")
        op.drop_column("users", "phone")
