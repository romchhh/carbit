"""Revision ID: 003_telegram_avatar
Revises: 002_notifications
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("telegram_avatar_path", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("telegram_avatar_path")
