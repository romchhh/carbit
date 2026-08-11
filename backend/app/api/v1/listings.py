from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Listing, SearchQuery
from app.schemas.schemas import PaginatedListings, ListingOut
from app.services.listings.serialize import listing_to_out
from app.services.listings.duplicates import listing_out_with_mirrors
from app.services.comparisons.resolve import resolve_listings_for_ids
from app.services.parser.results import get_search_results_from_db
from app.services.telegram_channels.lazy_photos import (
    enqueue_listing_photos,
    ensure_telegram_listing_photos,
    listing_needs_photos,
    sync_telegram_photos_from_disk,
)
from app.services.auto_ria.lazy_photos import attach_auto_ria_gallery, auto_ria_needs_gallery

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("/search/{search_id}", response_model=PaginatedListings)
async def get_listings_for_search(
    search_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("newest"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    sq = await db.get(SearchQuery, search_id)
    if not sq or sq.user_id != user_id:
        return PaginatedListings(items=[], total=0, page=page, per_page=per_page, pages=0)

    return await get_search_results_from_db(
        db,
        sq,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
    )


@router.get("/batch", response_model=list[ListingOut])
async def batch_listings(
    ids: str = Query(..., min_length=1, description="Comma-separated listing ids, max 4"),
    db: AsyncSession = Depends(get_db),
):
    """Публічне завантаження кількох оголошень для порівняння / шарингу."""
    id_list = [part.strip() for part in ids.split(",") if part.strip()]
    if not id_list:
        raise HTTPException(400, "Вкажіть ids")
    if len(id_list) > 4:
        raise HTTPException(400, "Максимум 4 оголошення")
    return await resolve_listings_for_ids(db, id_list)


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(
    listing_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Публічний перегляд оголошення — без авторизації."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing_needs_photos(listing):
        await sync_telegram_photos_from_disk(db, listing)
        if listing_needs_photos(listing):
            await ensure_telegram_listing_photos(
                db,
                listing,
                max_photos=1,
                telethon_timeout=12.0,
            )
    elif auto_ria_needs_gallery(listing):
        await attach_auto_ria_gallery(db, listing)
    return await listing_out_with_mirrors(db, listing)


@router.post("/{listing_id}/ensure-photos", response_model=ListingOut)
async def ensure_listing_photos(
    listing_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Завантажує фото Telegram (мін. 1) або ставить у чергу worker."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing_needs_photos(listing):
        await ensure_telegram_listing_photos(
            db,
            listing,
            max_photos=1,
            telethon_timeout=25.0,
        )
    elif auto_ria_needs_gallery(listing):
        await attach_auto_ria_gallery(db, listing)
    out = await listing_out_with_mirrors(db, listing)
    if not out.images:
        out = out.model_copy(
            update={
                "source_data": {
                    **(out.source_data or {}),
                    "photos_pending": True,
                }
            }
        )
    return out
