"""Revision ID: 004_parser_pipeline
Revises: 003
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parse_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("triggered_by", sa.String(), nullable=False),
        sa.Column("filter_groups", sa.Integer(), nullable=False),
        sa.Column("searches_processed", sa.Integer(), nullable=False),
        sa.Column("listings_found", sa.Integer(), nullable=False),
        sa.Column("listings_new", sa.Integer(), nullable=False),
        sa.Column("notifications_sent", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("log", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "search_listings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("search_id", sa.String(), nullable=False),
        sa.Column("listing_id", sa.String(), nullable=False),
        sa.Column("is_new", sa.Boolean(), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["search_id"], ["search_queries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("search_id", "listing_id", name="uq_search_listings_search_listing"),
    )
    op.create_index("ix_search_listings_search_id", "search_listings", ["search_id"])
    op.create_index("ix_search_listings_listing_id", "search_listings", ["listing_id"])


def downgrade() -> None:
    op.drop_index("ix_search_listings_listing_id", table_name="search_listings")
    op.drop_index("ix_search_listings_search_id", table_name="search_listings")
    op.drop_table("search_listings")
    op.drop_table("parse_runs")
