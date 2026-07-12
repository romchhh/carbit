"""Revision ID: 006_telegram_channels
Revises: 005
Create Date: 2026-07-12
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None

DEFAULT_CHANNELS = [
    "@ua_autobazar",
    "@auto_amerika_europa",
    "@autobazarlvivua",
    "@CarsBidPro",
    "@avtoUAeuro",
    "@kievautotrade",
    "@isAuto99",
    "@kievavto2",
]


def _normalize(raw: str) -> str | None:
    value = (raw or "").strip()
    if not value:
        return None
    if "t.me/" in value:
        value = value.split("t.me/", 1)[-1]
    value = value.split("?")[0].strip("/").lstrip("@").split("/")[0].strip()
    if not value or value.lstrip("-").isdigit():
        return None
    return f"@{value}"


def _seed_usernames() -> list[str]:
    env_raw = os.getenv("TELEGRAM_CHANNELS") or os.getenv("DEFAULT_CHANNELS") or ""
    from_env = [_normalize(part) for part in env_raw.split(",")]
    from_env = [item for item in from_env if item]
    if from_env:
        return list(dict.fromkeys(from_env))
    return list(DEFAULT_CHANNELS)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        tables = {
            row[0]
            for row in bind.execute(
                sa.text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "telegram_channels" in tables:
            return
    else:
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'telegram_channels'"
            )
        ).first()
        if exists:
            return

    op.create_table(
        "telegram_channels",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_telegram_channels_username", "telegram_channels", ["username"])

    channels = _seed_usernames()
    if not channels:
        return

    now = datetime.now(timezone.utc)
    table = sa.table(
        "telegram_channels",
        sa.column("id", sa.String),
        sa.column("username", sa.String),
        sa.column("title", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        table,
        [
            {
                "id": str(uuid.uuid4()),
                "username": username,
                "title": None,
                "enabled": True,
                "sort_order": index,
                "created_at": now,
            }
            for index, username in enumerate(channels)
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_telegram_channels_username", table_name="telegram_channels")
    op.drop_table("telegram_channels")
