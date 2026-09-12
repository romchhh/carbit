from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
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
    telethon_unavailable_reason,
)
from app.services.auto_ria.lazy_photos import attach_auto_ria_gallery, auto_ria_needs_gallery
from app.services.reono.errors import ReonoError
from app.services.reono.lazy_photos import fetch_reono_listing_images
from app.services.listings.gallery_fetch import fetch_listing_gallery, gallery_needs_fetch
from app.services.listings.seller_contact import apply_seller_contact_fields

router = APIRouter(prefix="/listings", tags=["listings"])


class ReonoPhotosRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=4096)


class ReonoPhotosResponse(BaseModel):
    images: list[str]


class ListingGalleryRequest(BaseModel):
    source: str = Field(..., min_length=2, max_length=32)
    listing_id: str | None = Field(default=None, max_length=128)
    url: str | None = Field(default=None, max_length=4096)
    images: list[str] = Field(default_factory=list)


class ListingGalleryResponse(BaseModel):
    images: list[str]
    seller_name: str | None = None
    seller_phone: str | None = None
    seller_telegram: str | None = None
    seller_url: str | None = None
    vin: str | None = None
    plate: str | None = None
    vin_checked: bool | None = None
    vin_check_url: str | None = None
    description: str | None = None
    had_accident: bool | None = None
    usa_import: bool | None = None
    engine_volume_l: float | None = None
    fuel: str | None = None
    transmission: str | None = None
    year: int | None = None
    mileage: int | None = None
    region: str | None = None
    source_data: dict | None = None


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


@router.post("/reono/photos", response_model=ReonoPhotosResponse)
async def reono_listing_photos(body: ReonoPhotosRequest):
    """Завантажує галерею REONO зі сторінки оголошення (пошук без БД)."""
    try:
        images = await fetch_reono_listing_images(body.url)
    except ReonoError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ReonoPhotosResponse(images=images)


def _gallery_listing_patch(result) -> dict:
    patch = {
        "seller_name": result.seller_name,
        "seller_phone": result.seller_phone,
        "seller_telegram": result.seller_telegram,
        "seller_url": result.seller_url,
        "vin": result.vin,
        "plate": result.plate,
        "vin_checked": result.vin_checked,
        "vin_check_url": result.vin_check_url,
        "description": result.description,
        "had_accident": result.had_accident,
        "usa_import": result.usa_import,
        "engine_volume_l": result.engine_volume_l,
        "fuel": result.fuel,
        "transmission": result.transmission,
        "year": result.year,
        "mileage": result.mileage,
        "region": result.region,
        "source_data": result.source_data,
    }
    return {key: value for key, value in patch.items() if value not in (None, "", [], {})}


def _auto_ria_needs_official_info(source: str, listing_id: str | None, source_data: dict | None) -> bool:
    key = (source or "").strip().lower()
    lid = listing_id or ""
    if key not in ("auto_ria",) and not lid.startswith(("auto_ria_", "new_auto_ria_")):
        return False
    sd = source_data if isinstance(source_data, dict) else {}
    return not (sd.get("autoData") or sd.get("checkedVin"))


async def _apply_gallery_to_listing(db: AsyncSession, listing: Listing) -> ListingOut:
    source = (listing.source or "").strip().lower()
    images = list(listing.images or [])
    needs_info = _auto_ria_needs_official_info(
        source,
        listing.id,
        getattr(listing, "source_data", None),
    )
    if needs_info or gallery_needs_fetch(source, images):
        result = await fetch_listing_gallery(
            source,
            listing_id=listing.id,
            url=listing.url,
            images=images,
        )
        if result.images:
            listing.images = result.images
        contact = {
            "seller_name": result.seller_name,
            "seller_phone": result.seller_phone,
            "seller_telegram": result.seller_telegram,
            "seller_url": result.seller_url,
        }
        out = await listing_out_with_mirrors(db, listing)
        patch = _gallery_listing_patch(result)
        if patch.get("source_data") and isinstance(out.source_data, dict):
            patch["source_data"] = {**out.source_data, **patch["source_data"]}
        if patch:
            out = out.model_copy(update=patch)
        return apply_seller_contact_fields(out, contact)
    return await listing_out_with_mirrors(db, listing)


@router.post("/gallery", response_model=ListingGalleryResponse)
async def listing_gallery(body: ListingGalleryRequest):
    """Повна галерея + контакти продавця для live-пошуку (без запису в БД)."""
    source = body.source.strip().lower()
    if source not in ("auto_ria", "auto_ria_beta", "olx", "imperiya"):
        raise HTTPException(status_code=400, detail="Джерело не підтримується")
    result = await fetch_listing_gallery(
        source,
        listing_id=body.listing_id,
        url=body.url,
        images=body.images,
    )
    return ListingGalleryResponse(
        images=result.images,
        seller_name=result.seller_name,
        seller_phone=result.seller_phone,
        seller_telegram=result.seller_telegram,
        seller_url=result.seller_url,
        vin=result.vin,
        plate=result.plate,
        vin_checked=result.vin_checked,
        vin_check_url=result.vin_check_url,
        description=result.description,
        had_accident=result.had_accident,
        usa_import=result.usa_import,
        engine_volume_l=result.engine_volume_l,
        fuel=result.fuel,
        transmission=result.transmission,
        year=result.year,
        mileage=result.mileage,
        region=result.region,
        source_data=result.source_data,
    )


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(
    listing_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Публічний перегляд оголошення — без авторизації."""
    from app.services.auto_ria.url_parse import listing_id_from_external_url
    from app.services.comparisons.resolve import _resolve_live_listing

    lid = listing_id_from_external_url(listing_id) or listing_id.strip()
    listing = await db.get(Listing, lid)
    if not listing:
        live = await _resolve_live_listing(lid)
        if live:
            return live
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
    elif auto_ria_needs_gallery(listing) or _auto_ria_needs_official_info(
        listing.source.value if hasattr(listing.source, "value") else str(listing.source),
        listing.id,
        getattr(listing, "source_data", None),
    ):
        return await _apply_gallery_to_listing(db, listing)
    elif gallery_needs_fetch((listing.source or "").lower(), list(listing.images or [])):
        return await _apply_gallery_to_listing(db, listing)
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
    elif gallery_needs_fetch((listing.source or "").lower(), list(listing.images or [])):
        return await _apply_gallery_to_listing(db, listing)

    out = await listing_out_with_mirrors(db, listing)
    if not out.images:
        # Якщо Telethon недоступний (розлогінена сесія) — кажемо це прямо,
        # інакше клієнт нескінченно опитує «фото ще вантажаться».
        unavailable = telethon_unavailable_reason()
        out = out.model_copy(
            update={
                "source_data": {
                    **(out.source_data or {}),
                    "photos_pending": not unavailable,
                    "photos_unavailable": bool(unavailable),
                }
            }
        )
    return out
