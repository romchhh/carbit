from __future__ import annotations

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.services.parser.runner import run_parser_for_search

logger = logging.getLogger(__name__)


async def background_parse_search(search_id: str) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await run_parser_for_search(db, search_id)
            await db.commit()
        except Exception:
            logger.exception("Background parse failed for search %s", search_id)
            await db.rollback()


def schedule_parse_search(search_id: str) -> None:
    asyncio.create_task(background_parse_search(search_id))
