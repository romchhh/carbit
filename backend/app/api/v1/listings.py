from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Listing, SearchQuery
from app.schemas.schemas import PaginatedListings, ListingOut
from app.services.listings.serialize import listing_to_out
from app.services.parser.results import get_search_results_from_db
from app.services.telegram_channels.lazy_photos import (
    enqueue_listing_photos,
    listing_needs_photos,
)

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


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(
    listing_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Публічний перегляд оголошення — без авторизації."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    # Відкрили картку без фото → ставимо в чергу воркера
    if listing_needs_photos(listing):
        enqueue_listing_photos(listing.id)
    return listing_to_out(listing)


@router.post("/{listing_id}/ensure-photos", response_model=ListingOut)
async def ensure_listing_photos(
    listing_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Ставить lazy-download у чергу Telegram worker і повертає поточний стан."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing_needs_photos(listing):
        enqueue_listing_photos(listing.id)
    out = listing_to_out(listing)
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
