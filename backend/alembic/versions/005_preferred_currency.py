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


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("preferred_currency", sa.String(), nullable=False, server_default="UAH")
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("preferred_currency")
