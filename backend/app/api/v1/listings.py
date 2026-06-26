from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Listing, SearchQuery
from app.schemas.schemas import PaginatedListings, ListingOut

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("/search/{search_id}", response_model=PaginatedListings)
async def get_listings_for_search(
    search_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("price_asc"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    sq = await db.get(SearchQuery, search_id)
    if not sq or sq.user_id != user_id:
        return PaginatedListings(items=[], total=0, page=page, per_page=per_page, pages=0)

    filters_dict = sq.filters
    conditions = [Listing.is_duplicate.is_(False)]

    if brand := filters_dict.get("brand"):
        conditions.append(Listing.brand.ilike(f"%{brand}%"))
    if model := filters_dict.get("model"):
        conditions.append(Listing.model.ilike(f"%{model}%"))
    if year_from := filters_dict.get("year_from"):
        conditions.append(Listing.year >= year_from)
    if year_to := filters_dict.get("year_to"):
        conditions.append(Listing.year <= year_to)
    if price_from := filters_dict.get("price_from"):
        conditions.append(Listing.price >= price_from)
    if price_to := filters_dict.get("price_to"):
        conditions.append(Listing.price <= price_to)
    if region := filters_dict.get("region"):
        conditions.append(Listing.region.ilike(f"%{region}%"))
    if fuels := filters_dict.get("fuel"):
        conditions.append(Listing.fuel.in_(fuels))
    if trans := filters_dict.get("transmission"):
        conditions.append(Listing.transmission.in_(trans))
    if sources := filters_dict.get("sources"):
        conditions.append(Listing.source.in_(sources))

    where = and_(*conditions)
    total = await db.scalar(select(func.count()).select_from(Listing).where(where))

    order = Listing.price.asc() if sort_by == "price_asc" else Listing.found_at.desc()
    result = await db.scalars(
        select(Listing).where(where).order_by(order).offset((page - 1) * per_page).limit(per_page)
    )
    items = result.all()

    return PaginatedListings(
        items=items,
        total=total or 0,
        page=page,
        per_page=per_page,
        pages=((total or 0) + per_page - 1) // per_page,
    )


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(
    listing_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing
