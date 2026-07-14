from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Favorite, Listing
from app.schemas.schemas import FavoriteOut, FavoriteCreate, FavoriteCheckBatch
from app.services.listings.upsert import upsert_listing_with_mirrors
from app.services.listings.duplicates import listing_out_with_mirrors

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("/list", response_model=list[FavoriteOut])
@router.get("", response_model=list[FavoriteOut], include_in_schema=False)
@router.get("/", response_model=list[FavoriteOut], include_in_schema=False)
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
            out.append(
                FavoriteOut(
                    id=fav.id,
                    listing_id=fav.listing_id,
                    listing=await listing_out_with_mirrors(db, listing),
                    created_at=fav.created_at,
                )
            )
    return out


@router.post("/check", response_model=dict)
async def check_favorites_batch(
    body: FavoriteCheckBatch,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not body.listing_ids:
        return {"ids": []}

    result = await db.scalars(
        select(Favorite.listing_id).where(
            Favorite.user_id == user_id,
            Favorite.listing_id.in_(body.listing_ids),
        )
    )
    return {"ids": list(result.all())}


@router.post("/add", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def add_favorite(
    body: FavoriteCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(Listing, body.listing_id)
    if not listing:
        if body.listing:
            listing = await upsert_listing_with_mirrors(db, body.listing)
        else:
            raise HTTPException(
                400,
                "Оголошення ще не в базі. Передайте дані listing для збереження з AUTO.RIA.",
            )
    elif body.listing and body.listing.alternate_sources:
        listing = await upsert_listing_with_mirrors(db, body.listing)

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
            listing=await listing_out_with_mirrors(db, listing),
            created_at=existing.created_at,
        )

    fav = Favorite(user_id=user_id, listing_id=body.listing_id)
    db.add(fav)
    await db.flush()
    return FavoriteOut(
        id=fav.id,
        listing_id=fav.listing_id,
        listing=await listing_out_with_mirrors(db, listing),
        created_at=fav.created_at,
    )


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
