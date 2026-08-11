"""Performance indexes for Telegram search and general listing queries.

Revision ID: 015
Revises: 014
Create Date: 2026-08-11
"""

from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def _index_exists(index_name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type='index' AND name=:n"),
            {"n": index_name},
        ).fetchall()
    else:
        rows = bind.execute(
            sa.text(
                "SELECT 1 FROM pg_indexes WHERE indexname = :n"
            ),
            {"n": index_name},
        ).fetchall()
    return bool(rows)


def upgrade() -> None:
    # Головний індекс для Telegram live-пошуку:
    # WHERE source = 'telegram' AND published_at >= ? ORDER BY published_at DESC LIMIT ?
    if not _index_exists("ix_listings_source_published_at"):
        op.create_index(
            "ix_listings_source_published_at",
            "listings",
            ["source", sa.text("published_at DESC")],
            postgresql_using="btree",
        )

    # Прискорює моніторинг + пошук за датою знаходження
    if not _index_exists("ix_listings_source_found_at"):
        op.create_index(
            "ix_listings_source_found_at",
            "listings",
            ["source", sa.text("found_at DESC")],
            postgresql_using="btree",
        )

    # Прискорює фільтр по бренду + сортування по published_at
    if not _index_exists("ix_listings_brand_published_at"):
        op.create_index(
            "ix_listings_brand_published_at",
            "listings",
            ["brand", sa.text("published_at DESC")],
            postgresql_using="btree",
        )

    # source окремо (WHERE source = ? — без published_at)
    if not _index_exists("ix_listings_source"):
        op.create_index(
            "ix_listings_source",
            "listings",
            ["source"],
        )


def downgrade() -> None:
    for name in (
        "ix_listings_brand_published_at",
        "ix_listings_source_found_at",
        "ix_listings_source_published_at",
        "ix_listings_source",
    ):
        if _index_exists(name):
            op.drop_index(name, table_name="listings")
