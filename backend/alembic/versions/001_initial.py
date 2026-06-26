"""initial schema

Revision ID: 001
Create Date: 2026-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("hashed_password", sa.String, nullable=True),
        sa.Column("google_id", sa.String, nullable=True, unique=True),
        sa.Column("telegram_id", sa.String, nullable=True, unique=True),
        sa.Column("plan", sa.String, nullable=False, default="free"),
        sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_connected", sa.Boolean, default=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "search_queries",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("filters", sa.JSON),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("new_count", sa.Integer, default=0),
        sa.Column("total_count", sa.Integer, default=0),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "listings",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("external_id", sa.String, nullable=False, index=True),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("title", sa.String),
        sa.Column("brand", sa.String, index=True),
        sa.Column("model", sa.String, index=True),
        sa.Column("year", sa.Integer),
        sa.Column("price", sa.Integer),
        sa.Column("currency", sa.String, default="UAH"),
        sa.Column("mileage", sa.Integer),
        sa.Column("fuel", sa.String),
        sa.Column("transmission", sa.String),
        sa.Column("region", sa.String),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("images", sa.JSON),
        sa.Column("url", sa.String),
        sa.Column("seller_name", sa.String, nullable=True),
        sa.Column("seller_type", sa.String, default="private"),
        sa.Column("price_history", sa.JSON),
        sa.Column("is_duplicate", sa.Boolean, default=False),
        sa.Column("duplicate_of", sa.String, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("found_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "favorites",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("listing_id", sa.String, sa.ForeignKey("listings.id", ondelete="CASCADE")),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )


def downgrade():
    op.drop_table("favorites")
    op.drop_table("listings")
    op.drop_table("search_queries")
    op.drop_table("users")
