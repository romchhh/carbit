from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import User, SearchQuery
from app.schemas.schemas import SearchQueryCreate, SearchQueryUpdate, SearchQueryOut

router = APIRouter(prefix="/searches", tags=["searches"])


async def _get_user(user_id: str, db: AsyncSession) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.get("/", response_model=list[SearchQueryOut])
async def list_searches(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.scalars(
        select(SearchQuery).where(SearchQuery.user_id == user_id).order_by(SearchQuery.created_at.desc())
    )
    return result.all()


@router.post("/", response_model=SearchQueryOut, status_code=201)
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
