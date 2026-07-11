from __future__ import annotations

import logging

from fastapi import HTTPException

from app.core.database import AsyncSessionLocal
from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.errors import raise_auto_ria_http
from app.services.auto_ria.preview_limits import clamp_preview_request, consume_preview_quota, is_preview_mode
from app.services.olx.errors import OlxError, raise_olx_http
from app.services.parser.results import get_cached_preview_results
from app.services.parser.runner import ingest_preview_results
from app.services.search.multi_source import search_listings

logger = logging.getLogger(__name__)


async def run_live_search(
    filters: SearchFilters,
    *,
    user_id: str,
    page: int,
    per_page: int,
    sort_by: str,
    mode: str,
) -> PaginatedListings:
    if is_preview_mode(mode) and page == 1:
        await consume_preview_quota(user_id)

    page, per_page = clamp_preview_request(page=page, per_page=per_page, mode=mode)

    # Кеш preview зберігає першу порцію + total — пагінацію (page>1) завжди беремо з джерел
    if page == 1:
        try:
            async with AsyncSessionLocal() as db:
                cached = await get_cached_preview_results(
                    db,
                    filters,
                    page=page,
                    per_page=per_page,
                    sort_by=sort_by,
                )
                if cached is not None:
                    return cached
        except Exception:
            logger.exception("Preview cache read failed — falling back to live search")

    try:
        results = await search_listings(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            use_cache=False,
            db=None,
        )
    except AutoRiaError as exc:
        raise_auto_ria_http(exc)
    except OlxError as exc:
        raise_olx_http(exc)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Live search failed")
        raise HTTPException(
            502,
            "Пошук тимчасово недоступний. Спробуйте ще раз за хвилину.",
        ) from exc

    if page == 1:
        async with AsyncSessionLocal() as db:
            try:
                await ingest_preview_results(
                    db,
                    filters,
                    results.items,
                    total=results.total,
                    pages=results.pages,
                )
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("Failed to ingest preview results")

    return results
