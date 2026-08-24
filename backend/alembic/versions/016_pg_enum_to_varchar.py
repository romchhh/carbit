"""PostgreSQL: convert legacy native ENUM columns to VARCHAR (SQLAlchemy StrEnum).

Revision ID: 016
Revises: 015
"""

from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def _pg_enum_column(table: str, column: str, enum_name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    row = bind.execute(
        sa.text(
            """
            SELECT udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table
              AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).fetchone()
    return bool(row and row[0] == enum_name)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    if _pg_enum_column("monitoring_source_requests", "status", "sourcerequeststatus"):
        op.execute(
            "ALTER TABLE monitoring_source_requests "
            "ALTER COLUMN status TYPE VARCHAR(32) USING status::text"
        )
        op.execute("DROP TYPE IF EXISTS sourcerequeststatus")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    row = bind.execute(
        sa.text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'monitoring_source_requests'
              AND column_name = 'status'
            """
        )
    ).fetchone()
    if not row or row[0] != "character varying":
        return

    op.execute(
        "CREATE TYPE sourcerequeststatus AS ENUM "
        "('pending', 'in_review', 'approved', 'rejected')"
    )
    op.execute(
        "ALTER TABLE monitoring_source_requests "
        "ALTER COLUMN status TYPE sourcerequeststatus "
        "USING status::sourcerequeststatus"
    )
