from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import User, SearchQuery
from app.schemas.schemas import (
    PaginatedListings,
    SearchFilters,
    SearchLiveResultsOut,
    SearchQueryCreate,
    SearchQueryOut,
    SearchQueryUpdate,
)
from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.errors import raise_auto_ria_http
from app.services.auto_ria.search_endpoint import run_auto_ria_search
from app.services.auto_ria.service import search_auto_ria

router = APIRouter(prefix="/searches", tags=["searches"])


async def _get_user(user_id: str, db: AsyncSession) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.get("", response_model=list[SearchQueryOut])
async def list_searches(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.scalars(
        select(SearchQuery).where(SearchQuery.user_id == user_id).order_by(SearchQuery.created_at.desc())
    )
    return result.all()


@router.post("/live", response_model=PaginatedListings)
async def live_auto_ria_search(
    filters: SearchFilters,
    page: int = Query(1, ge=1),
    per_page: int = Query(5, ge=1, le=50),
    sort_by: str = Query("price_asc"),
    mode: str = Query("preview", pattern="^(preview|browse)$"),
    user_id: str = Depends(get_current_user_id),
):
    """Live AUTO.RIA search (preview/browse). Also exposed as POST /auto-ria/search."""
    return await run_auto_ria_search(
        filters,
        user_id=user_id,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        mode=mode,
    )


@router.get("/{search_id}", response_model=SearchQueryOut)
async def get_search(
    search_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    sq = await db.get(SearchQuery, search_id)
    if not sq or sq.user_id != user_id:
        raise HTTPException(404, "Search not found")
    return sq


@router.get("/{search_id}/results", response_model=SearchLiveResultsOut)
async def get_search_results(
    search_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    sort_by: str = Query("price_asc"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    sq = await db.get(SearchQuery, search_id)
    if not sq or sq.user_id != user_id:
        raise HTTPException(404, "Search not found")

    filters = SearchFilters.model_validate(sq.filters)
    try:
        results = await search_auto_ria(filters, page=page, per_page=per_page, sort_by=sort_by)
    except AutoRiaError as exc:
        raise_auto_ria_http(exc)

    sq.total_count = results.total
    sq.last_checked_at = datetime.now(UTC)
    await db.flush()

    return SearchLiveResultsOut(search=sq, results=results)


@router.post("", response_model=SearchQueryOut, status_code=201)
async def create_search(
    body: SearchQueryCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user(user_id, db)
    count = await db.scalar(
        select(func.count()).select_from(SearchQuery).where(SearchQuery.user_id == user_id)
    )
    if count >= user.searches_limit:
        raise HTTPException(403, f"Plan limit reached ({user.searches_limit} searches)")

    sq = SearchQuery(user_id=user_id, name=body.name, filters=body.filters.model_dump(exclude_none=True))
    db.add(sq)
    await db.flush()
    return sq


@router.patch("/{search_id}", response_model=SearchQueryOut)
async def update_search(
    search_id: str,
    body: SearchQueryUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    sq = await db.get(SearchQuery, search_id)
    if not sq or sq.user_id != user_id:
        raise HTTPException(404, "Search not found")

    for field, val in body.model_dump(exclude_none=True).items():
        if field == "filters":
            setattr(sq, field, val.model_dump(exclude_none=True) if hasattr(val, "model_dump") else val)
        else:
            setattr(sq, field, val)
    return sq


@router.delete("/{search_id}", status_code=204)
async def delete_search(
    search_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    sq = await db.get(SearchQuery, search_id)
    if not sq or sq.user_id != user_id:
        raise HTTPException(404, "Search not found")
    await db.delete(sq)
