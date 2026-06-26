"""002 notifications and user extensions

Revision ID: 002
Revises: 001
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("telegram_username", sa.String, nullable=True))
    op.add_column("users", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("onboarding_completed", sa.Boolean, server_default=sa.text("0")))

    op.create_table(
        "notifications",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("body", sa.String, nullable=False),
        sa.Column("listing_id", sa.String, sa.ForeignKey("listings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("search_id", sa.String, sa.ForeignKey("search_queries.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payload", sa.JSON, server_default=sa.text("'{}'")),
        sa.Column("is_read", sa.Boolean, server_default=sa.text("0")),
        sa.Column("sent_telegram", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("favorites") as batch_op:
            batch_op.create_unique_constraint("uq_favorites_user_listing", ["user_id", "listing_id"])
    else:
        op.create_unique_constraint("uq_favorites_user_listing", "favorites", ["user_id", "listing_id"])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("favorites") as batch_op:
            batch_op.drop_constraint("uq_favorites_user_listing", type_="unique")
    else:
        op.drop_constraint("uq_favorites_user_listing", "favorites", type_="unique")
    op.drop_table("notifications")
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "trial_ends_at")
    op.drop_column("users", "telegram_username")
