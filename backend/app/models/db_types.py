"""SQLAlchemy column types shared across models."""

from __future__ import annotations

import enum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

_E = TypeVar("_E", bound=enum.Enum)


def StrEnum(enum_cls: type[_E], **kwargs) -> SAEnum:
    """Store enum values as VARCHAR (Alembic migrations + SQLite import)."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        values_callable=lambda obj: [member.value for member in obj],
        **kwargs,
    )
