from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.services.parser.results import get_search_results_from_db, mark_search_listings_seen
from app.services.parser.tasks import schedule_parse_search
from app.services.search.search_endpoint import run_live_search

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
async def live_search(
    filters: SearchFilters,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    sort_by: str = Query("price_asc"),
    mode: str = Query("preview", pattern="^(preview|browse)$"),
    user_id: str = Depends(get_current_user_id),
):
    """Live multi-source search (AUTO.RIA + OLX). Also exposed as POST /auto-ria/search."""
    return await run_live_search(
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
    sort_by: str = Query("newest"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    sq = await db.get(SearchQuery, search_id)
    if not sq or sq.user_id != user_id:
        raise HTTPException(404, "Search not found")

    results = await get_search_results_from_db(
        db,
        sq,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
    )

    if page == 1:
        await mark_search_listings_seen(db, sq)

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
    schedule_parse_search(sq.id)
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
