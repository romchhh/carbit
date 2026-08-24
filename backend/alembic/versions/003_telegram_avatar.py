"""Revision ID: 003_telegram_avatar
Revises: 002_notifications
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

from app.migrations.dialect_helpers import has_column

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if has_column("users", "telegram_avatar_path"):
        return
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("telegram_avatar_path", sa.String(), nullable=True))
    else:
        op.add_column("users", sa.Column("telegram_avatar_path", sa.String(), nullable=True))


def downgrade() -> None:
    if not has_column("users", "telegram_avatar_path"):
        return
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("telegram_avatar_path")
    else:
        op.drop_column("users", "telegram_avatar_path")
