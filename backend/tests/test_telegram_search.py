from __future__ import annotations

import asyncio
import unittest

from app.core.database import AsyncSessionLocal
from app.schemas.schemas import SearchFilters
from app.services.telegram_channels.ingest import search_telegram_listings
from app.services.telegram_channels.mapper import listing_out_matches_filters


class TelegramSearchTests(unittest.TestCase):
    def test_porsche_listing_matches_kyiv_search(self):
        item = type("Item", (), {
            "brand": "Porsche",
            "model": "MACAN S",
            "title": "Porsche MACAN S 2018",
            "year": 2018,
            "price": 631_400,
            "currency": "UAH",
            "mileage": 50_000,
            "region": "Україна",
            "source": "telegram",
            "fuel": "",
            "transmission": "",
            "description": "",
        })()
        filters = SearchFilters.model_validate({
            "brand": "Porsche",
            "year_from": 2010,
            "year_to": 2024,
            "price_from": 400_000,
            "price_to": 2_000_000,
            "currency": "UAH",
            "region": "м. Київ",
            "sources": ["telegram"],
        })
        self.assertTrue(listing_out_matches_filters(item, filters))

    def test_unknown_year_rejected_when_year_filter_set(self):
        item = type("Item", (), {
            "brand": "Zeekr",
            "model": "001",
            "title": "Zeekr 001",
            "year": 0,
            "price": 1_500_000,
            "currency": "UAH",
            "mileage": 10_000,
            "region": "Україна",
            "source": "telegram",
            "fuel": "Електро",
            "transmission": "",
            "description": "",
        })()
        filters = SearchFilters.model_validate({
            "brand": "Zeekr",
            "model": "001",
            "year_from": 2018,
            "year_to": 2026,
            "sources": ["telegram"],
        })
        self.assertFalse(listing_out_matches_filters(item, filters))

    def test_region_blocks_non_telegram_without_city(self):
        item = type("Item", (), {
            "brand": "Porsche",
            "model": "MACAN S",
            "title": "Porsche MACAN S 2018",
            "year": 2018,
            "price": 631_400,
            "mileage": 50_000,
            "region": "Україна",
            "source": "olx",
            "fuel": "",
            "transmission": "",
            "description": "",
        })()
        filters = SearchFilters.model_validate({
            "brand": "Porsche",
            "region": "м. Київ",
            "sources": ["olx"],
        })
        self.assertFalse(listing_out_matches_filters(item, filters))


async def _count_porsche_in_db() -> int:
    async with AsyncSessionLocal() as db:
        filters = SearchFilters.model_validate({
            "brand": "Porsche",
            "year_from": 2010,
            "year_to": 2024,
            "price_from": 40_000,
            "price_to": 90_000_000,
            "region": "м. Київ",
            "sources": ["telegram"],
        })
        result = await search_telegram_listings(db, filters, per_page=50)
        return len(result.items)


class TelegramDbSearchTests(unittest.TestCase):
    def test_existing_porsche_listings_match(self):
        count = asyncio.run(_count_porsche_in_db())
        self.assertGreaterEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
