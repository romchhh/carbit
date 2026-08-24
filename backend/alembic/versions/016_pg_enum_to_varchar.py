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


def _pg_type_exists(type_name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    row = bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": type_name},
    ).fetchone()
    return bool(row)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    table = "monitoring_source_requests"
    column = "status"
    enum_name = "sourcerequeststatus"

    if not (
        _pg_enum_column(table, column, enum_name)
        or _pg_type_exists(enum_name)
    ):
        return

    # Default `'pending'::sourcerequeststatus` blocks DROP TYPE — знімаємо спочатку.
    op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT")

    if _pg_enum_column(table, column, enum_name):
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} TYPE VARCHAR(32) USING {column}::text"
        )

    op.execute(
        f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT 'pending'"
    )

    if _pg_type_exists(enum_name):
        op.execute(f"DROP TYPE {enum_name}")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    table = "monitoring_source_requests"
    column = "status"
    enum_name = "sourcerequeststatus"

    row = bind.execute(
        sa.text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table
              AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).fetchone()
    if not row or row[0] != "character varying":
        return

    if not _pg_type_exists(enum_name):
        op.execute(
            f"CREATE TYPE {enum_name} AS ENUM "
            "('pending', 'in_review', 'approved', 'rejected')"
        )

    op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT")
    op.execute(
        f"ALTER TABLE {table} "
        f"ALTER COLUMN {column} TYPE {enum_name} "
        f"USING {column}::{enum_name}"
    )
    op.execute(
        f"ALTER TABLE {table} "
        f"ALTER COLUMN {column} SET DEFAULT 'pending'::{enum_name}"
    )
