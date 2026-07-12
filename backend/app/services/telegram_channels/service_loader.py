from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.telegram_channels.bootstrap import ensure_parser_path


def get_parser_service(*, fresh_dedupe: bool = False, skip_dedupe: bool = False):
    ensure_parser_path()
    from parser.service import CarParserService

    return CarParserService(fresh_dedupe=fresh_dedupe, skip_dedupe=skip_dedupe)


async def get_parser_channels(db: AsyncSession | None = None) -> list[str]:
    """Активні Telegram-канали з БД (адмінка)."""
    from app.core.database import AsyncSessionLocal
    from app.services.telegram_channels.channels import list_enabled_usernames

    if db is not None:
        return await list_enabled_usernames(db)

    async with AsyncSessionLocal() as session:
        return await list_enabled_usernames(session)
