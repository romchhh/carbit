from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Favorite, Listing
from app.schemas.schemas import FavoriteOut, FavoriteCreate

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("/", response_model=list[FavoriteOut])
async def list_favorites(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.scalars(
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
    )
    favorites = result.all()
    out = []
    for fav in favorites:
        listing = await db.get(Listing, fav.listing_id)
        if listing:
            out.append(FavoriteOut(
                id=fav.id,
                listing_id=fav.listing_id,
                listing=listing,
                created_at=fav.created_at,
            ))
    return out


@router.post("/", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
async def add_favorite(
    body: FavoriteCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(Listing, body.listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")

    existing = await db.scalar(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.listing_id == body.listing_id,
        )
    )
    if existing:
        return FavoriteOut(
            id=existing.id,
            listing_id=existing.listing_id,
            listing=listing,
            created_at=existing.created_at,
        )

    fav = Favorite(user_id=user_id, listing_id=body.listing_id)
    db.add(fav)
    await db.flush()
    return FavoriteOut(id=fav.id, listing_id=fav.listing_id, listing=listing, created_at=fav.created_at)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    listing_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    fav = await db.scalar(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.listing_id == listing_id)
    )
    if not fav:
        raise HTTPException(404, "Favorite not found")
    await db.delete(fav)


@router.get("/check/{listing_id}")
async def check_favorite(
    listing_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    fav = await db.scalar(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.listing_id == listing_id)
    )
    return {"is_favorite": fav is not None}
