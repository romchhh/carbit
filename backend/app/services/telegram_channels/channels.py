from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import now_kyiv
from app.models.models import Listing, Source, TelegramChannel


def normalize_channel_username(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Вкажіть username каналу")
    lower = raw.lower()
    if "joinchat/" in lower:
        invite = raw.split("joinchat/", 1)[-1].split("?")[0].strip("/")
        if not invite:
            raise ValueError("Невірне інвайт-посилання")
        return f"https://t.me/joinchat/{invite}"
    if "t.me/" in lower:
        tail = raw.split("t.me/", 1)[-1].split("?")[0].strip("/")
        if tail.startswith("+"):
            return f"https://t.me/{tail}"
        raw = tail
    raw = raw.split("?")[0].strip("/").split("/")[0].strip()
    if raw.startswith("@"):
        raw = raw.lstrip("@")
    if raw.startswith("+"):
        return f"https://t.me/{raw}"
    if not raw:
        raise ValueError("Невірний username каналу")
    if raw.lstrip("-").isdigit():
        raise ValueError("Потрібен публічний @username, не числовий id")
    return f"@{raw}"


def channel_slug(username: str) -> str:
    raw = (username or "").strip()
    if "t.me/" in raw.lower():
        tail = raw.split("t.me/", 1)[-1].split("?")[0].strip("/")
        if tail.startswith("+"):
            return tail.lstrip("+")
        return tail.split("/")[0].lstrip("@")
    return raw.lstrip("@").lstrip("+")


def parser_channel_ref(username: str) -> str:
    """Формат для Telethon (після normalize в БД)."""
    raw = (username or "").strip()
    if raw.startswith("@+"):
        return f"https://t.me/{raw[1:]}"
    return raw


async def list_channels(db: AsyncSession, *, enabled_only: bool = False) -> list[TelegramChannel]:
    stmt = select(TelegramChannel).order_by(TelegramChannel.sort_order, TelegramChannel.created_at)
    if enabled_only:
        stmt = stmt.where(TelegramChannel.enabled.is_(True))
    rows = await db.scalars(stmt)
    return list(rows.all())


async def list_enabled_usernames(db: AsyncSession) -> list[str]:
    channels = await list_channels(db, enabled_only=True)
    return [parser_channel_ref(channel.username) for channel in channels]


async def get_channel(db: AsyncSession, channel_id: str) -> TelegramChannel | None:
    return await db.get(TelegramChannel, channel_id)


async def create_channel(
    db: AsyncSession,
    *,
    username: str,
    title: str | None = None,
    enabled: bool = True,
) -> TelegramChannel:
    normalized = normalize_channel_username(username)
    existing = await db.scalar(
        select(TelegramChannel).where(TelegramChannel.username == normalized)
    )
    if existing:
        raise ValueError(f"Канал {normalized} уже додано")

    max_order = await db.scalar(select(func.max(TelegramChannel.sort_order))) or 0
    channel = TelegramChannel(
        username=normalized,
        title=(title or "").strip() or None,
        enabled=enabled,
        sort_order=int(max_order) + 1,
        created_at=now_kyiv(),
    )
    db.add(channel)
    await db.flush()
    return channel


async def update_channel(
    db: AsyncSession,
    channel: TelegramChannel,
    *,
    title: str | None = None,
    enabled: bool | None = None,
    sort_order: int | None = None,
    username: str | None = None,
) -> TelegramChannel:
    if username is not None:
        normalized = normalize_channel_username(username)
        if normalized != channel.username:
            clash = await db.scalar(
                select(TelegramChannel).where(
                    TelegramChannel.username == normalized,
                    TelegramChannel.id != channel.id,
                )
            )
            if clash:
                raise ValueError(f"Канал {normalized} уже додано")
            channel.username = normalized
    if title is not None:
        channel.title = title.strip() or None
    if enabled is not None:
        channel.enabled = enabled
    if sort_order is not None:
        channel.sort_order = sort_order
    await db.flush()
    return channel


async def delete_channel(db: AsyncSession, channel: TelegramChannel) -> None:
    await db.delete(channel)
    await db.flush()


async def count_channel_listings(db: AsyncSession, username: str) -> int:
    slug = channel_slug(username)
    if not slug:
        return 0
    stmt = (
        select(func.count())
        .select_from(Listing)
        .where(
            Listing.source == Source.telegram,
            or_(
                Listing.id.ilike(f"telegram_{slug}_%"),
                Listing.external_id.ilike(f"{slug}_%"),
                Listing.url.ilike(f"%t.me/{slug}/%"),
            ),
            Listing.is_duplicate.is_(False),
        )
    )
    return int(await db.scalar(stmt) or 0)


async def list_channel_listings(
    db: AsyncSession,
    username: str,
    *,
    limit: int = 40,
) -> list[Listing]:
    slug = channel_slug(username)
    if not slug:
        return []
    rows = await db.scalars(
        select(Listing)
        .where(
            Listing.source == Source.telegram,
            or_(
                Listing.id.ilike(f"telegram_{slug}_%"),
                Listing.external_id.ilike(f"{slug}_%"),
                Listing.url.ilike(f"%t.me/{slug}/%"),
            ),
            Listing.is_duplicate.is_(False),
        )
        .order_by(Listing.found_at.desc())
        .limit(limit)
    )
    return list(rows.all())
