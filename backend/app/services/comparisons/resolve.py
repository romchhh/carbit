"""Завантаження оголошень для порівняння."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing
from app.schemas.schemas import ListingOut
from app.services.listings.duplicates import listing_out_with_mirrors

logger = logging.getLogger(__name__)


async def _resolve_live_listing(listing_id: str) -> ListingOut | None:
    lid = str(listing_id or "").strip()
    if not lid:
        return None

    if lid.startswith("olx_"):
        numeric = lid.removeprefix("olx_")
        try:
            from app.services.olx.client import OlxClient
            from app.services.olx.mapper import olx_listing_to_listing_out

            async with OlxClient() as client:
                olx = await client.fetch_offer_by_id(numeric)
            if olx:
                return olx_listing_to_listing_out(olx)
        except Exception:
            logger.exception("Failed to fetch OLX listing id=%s", lid)
        return None

    if lid.startswith("new_auto_ria_") or lid.startswith("auto_ria_"):
        auto_id = lid.split("_", 2)[-1]
        try:
            from app.services.auto_ria.service import hydrate_auto_ria_ids

            items = await hydrate_auto_ria_ids([auto_id])
            return items[0] if items else None
        except Exception:
            logger.exception("Failed to hydrate AUTO.RIA listing id=%s", lid)
        return None

    return None


async def resolve_listings_for_ids(db: AsyncSession, listing_ids: list[str]) -> list[ListingOut]:
    items: list[ListingOut] = []
    seen: set[str] = set()
    for listing_id in listing_ids[:4]:
        lid = str(listing_id).strip()
        if not lid or lid in seen:
            continue
        seen.add(lid)

        listing = await db.get(Listing, lid)
        if listing:
            items.append(await listing_out_with_mirrors(db, listing))
            continue

        live = await _resolve_live_listing(lid)
        if live:
            items.append(live)
    return items
