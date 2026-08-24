"""Revision ID: 011_monitoring_source_requests
Revises: 010
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa


revision = "011"
down_revision = "010"
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
    if _has_table("monitoring_source_requests"):
        return
    op.create_table(
        "monitoring_source_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("admin_note", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_monitoring_source_requests_user_id",
        "monitoring_source_requests",
        ["user_id"],
    )
    op.create_index(
        "ix_monitoring_source_requests_status",
        "monitoring_source_requests",
        ["status"],
    )


def downgrade() -> None:
    if _has_table("monitoring_source_requests"):
        op.drop_table("monitoring_source_requests")
