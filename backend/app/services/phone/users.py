"""Допоміжні запити користувачів за телефоном."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User


async def get_verified_phone_user(db: AsyncSession, phone: str) -> User | None:
    return await db.scalar(
        select(User).where(
            User.phone == phone,
            User.phone_verified_at.isnot(None),
        )
    )


async def is_phone_taken(db: AsyncSession, phone: str, *, exclude_user_id: str | None = None) -> bool:
    q = select(User.id).where(
        User.phone == phone,
        User.phone_verified_at.isnot(None),
    )
    if exclude_user_id:
        q = q.where(User.id != exclude_user_id)
    row = await db.scalar(q)
    return row is not None
