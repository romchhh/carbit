"""Dialect-specific defaults for Alembic migrations (SQLite vs PostgreSQL)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


def bool_false_default() -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.text("0")
    return sa.text("false")


def json_empty_default() -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.text("'{}'")
    return sa.text("'{}'::json")


def has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
        return any(row[1] == column for row in rows)
    rows = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    ).fetchall()
    return bool(rows)


def has_table(table: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(
            sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:table"),
            {"table": table},
        ).fetchall()
        return bool(rows)
    rows = bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :table"),
        {"table": table},
    ).fetchall()
    return bool(rows)


def has_unique_constraint(table: str, name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(
            sa.text("SELECT 1 FROM sqlite_master WHERE type='index' AND name=:name"),
            {"name": name},
        ).fetchall()
        return bool(rows)
    rows = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = :table AND constraint_name = :name"
        ),
        {"table": table, "name": name},
    ).fetchall()
    return bool(rows)
