"""Revision ID: 017_personal_data_consent
Revises: 016
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa


revision = "017"
down_revision = "016"
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
    if not _has_column("users", "phone_otp_channel"):
        op.add_column("users", sa.Column("phone_otp_channel", sa.String(length=16), nullable=True))
    if not _has_column("users", "personal_data_consent_at"):
        op.add_column(
            "users",
            sa.Column("personal_data_consent_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_column("users", "personal_data_consent_version"):
        op.add_column(
            "users",
            sa.Column("personal_data_consent_version", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    if _has_column("users", "personal_data_consent_version"):
        op.drop_column("users", "personal_data_consent_version")
    if _has_column("users", "personal_data_consent_at"):
        op.drop_column("users", "personal_data_consent_at")
    if _has_column("users", "phone_otp_channel"):
        op.drop_column("users", "phone_otp_channel")
