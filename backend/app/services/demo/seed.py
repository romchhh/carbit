"""Seed demo listings for development without live API monitoring."""
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, Source, SearchQuery, User
from app.services.notifications.service import create_listing_notification

DEMO_LISTINGS = [
    {
        "external_id": "demo-001",
        "source": Source.auto_ria,
        "title": "Toyota Camry 2.5 AT",
        "brand": "Toyota", "model": "Camry", "year": 2021,
        "price": 780_000, "mileage": 45_000, "fuel": "Бензин",
        "transmission": "Автомат", "region": "Київ",
        "description": "Один власник, без ДТП.",
        "url": "https://auto.ria.com/demo/1",
    },
    {
        "external_id": "demo-002",
        "source": Source.olx,
        "title": "Volkswagen Passat B8 2.0 TDI",
        "brand": "Volkswagen", "model": "Passat", "year": 2019,
        "price": 620_000, "mileage": 112_000, "fuel": "Дизель",
        "transmission": "Автомат", "region": "Львів",
        "description": "Повна комплектація Highline.",
        "url": "https://olx.ua/demo/2",
    },
    {
        "external_id": "demo-003",
        "source": Source.telegram,
        "title": "Skoda Octavia A7 1.4 TSI",
        "brand": "Skoda", "model": "Octavia", "year": 2018,
        "price": 485_000, "mileage": 98_000, "fuel": "Бензин",
        "transmission": "Робот", "region": "Одеса",
        "description": "Торг доречний.",
        "url": "https://t.me/demo/3",
    },
]


async def seed_demo_listings(db: AsyncSession, user_id: str) -> dict:
    created = 0
    notifications = 0
    search = await db.scalar(
        select(SearchQuery).where(SearchQuery.user_id == user_id).limit(1)
    )
    user = await db.get(User, user_id)

    for raw in DEMO_LISTINGS:
        exists = await db.scalar(
            select(Listing).where(Listing.external_id == raw["external_id"])
        )
        if exists:
            listing = exists
        else:
            listing = Listing(
                **raw,
                currency="UAH",
                images=[],
                seller_type="private",
                price_history=[],
                published_at=datetime.now(UTC),
            )
            db.add(listing)
            await db.flush()
            created += 1

        if user:
            await create_listing_notification(db, user, listing, search)
            notifications += 1

    if search:
        search.new_count += notifications
        search.total_count += created
        search.last_checked_at = datetime.now(UTC)

    await db.flush()
    return {"listings_created": created, "notifications_sent": notifications}
