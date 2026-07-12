"""Revision ID: 007_default_usd
Revises: 006
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite: server_default на існуючій колонці не змінюємо жорстко;
        # нові користувачі отримують USD з ORM default.
        return
    op.alter_column(
        "users",
        "preferred_currency",
        existing_type=sa.String(),
        server_default="USD",
        existing_nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    op.alter_column(
        "users",
        "preferred_currency",
        existing_type=sa.String(),
        server_default="UAH",
        existing_nullable=False,
    )
