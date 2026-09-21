from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.services.listings.gallery_fetch import (
    fetch_auto_ria_gallery,
    fetch_olx_gallery,
    gallery_needs_fetch,
)


class GalleryFetchTests(unittest.IsolatedAsyncioTestCase):
    def test_gallery_needs_fetch_below_two_images(self):
        self.assertTrue(gallery_needs_fetch("olx", ["https://img/1.jpg"]))
        self.assertFalse(gallery_needs_fetch("olx", ["https://a/1.jpg", "https://a/2.jpg"]))
        self.assertFalse(gallery_needs_fetch("reono", []))

    async def test_fetch_auto_ria_uses_html_enrich(self):
        from datetime import datetime

        from app.core.timezone import KYIV_TZ
        from app.schemas.schemas import ListingOut

        enriched = ListingOut(
            id="auto_ria_123",
            source="auto_ria",
            title="BMW X5",
            url="https://auto.ria.com/uk/auto_bmw_x5_123.html",
            brand="BMW",
            model="X5",
            year=2020,
            price=25000,
            currency="USD",
            mileage=50000,
            fuel="Бензин",
            transmission="Автомат",
            region="Київ",
            description=None,
            images=["https://cdn.example.com/1f.jpg", "https://cdn.example.com/2f.jpg"],
            seller_type="dealer",
            seller_name="Test Dealer",
            vin="WBA8E9C50HK123456",
            vin_checked=True,
            source_data={"html_search": {"posted": "сьогодні"}},
            price_history=[],
            is_duplicate=False,
            published_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
            found_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
        )

        with patch(
            "app.services.listings.gallery_fetch.enrich_listing_from_html",
            new_callable=AsyncMock,
            return_value=enriched,
        ) as enrich_mock:
            result = await fetch_auto_ria_gallery(
                listing_id="auto_ria_123",
                url="https://auto.ria.com/auto_123.html",
                current_images=["https://cdn.example.com/cover.jpg"],
            )

        enrich_mock.assert_called_once()
        self.assertEqual(len(result.images), 2)
        self.assertEqual(result.seller_name, "Test Dealer")
        self.assertEqual(result.vin, "WBA8E9C50HK123456")
        self.assertTrue(result.vin_checked)
        self.assertIsInstance(result.source_data, dict)

    async def test_fetch_olx_always_loads_detail_gallery(self):
        olx_listing = type(
            "OlxListing",
            (),
            {
                "url": "https://www.olx.ua/d/uk/offer/test-ID.html",
                "photos": ["https://img/1.jpg", "https://img/2.jpg"],
                "photo_url": "https://img/1.jpg",
            },
        )()

        with patch("app.services.listings.gallery_fetch.OlxClient") as client_cls:
            client = client_cls.return_value
            client.fetch_offer_by_id = AsyncMock(return_value=olx_listing)
            client.fetch_listing_details = AsyncMock(
                return_value={
                    "photos": [
                        "https://img/1.jpg",
                        "https://img/2.jpg",
                        "https://img/3.jpg",
                    ],
                    "seller_name": "Іван",
                    "seller_url": "https://www.olx.ua/list/user/ivan/",
                    "description": "Телефон 097 555 44 33",
                }
            )

            result = await fetch_olx_gallery(
                listing_id="olx_ID",
                url=olx_listing.url,
                current_images=["https://img/1.jpg", "https://img/2.jpg"],
            )

        client.fetch_listing_details.assert_called_once()
        self.assertEqual(len(result.images), 3)
        self.assertEqual(result.seller_name, "Іван")
        self.assertEqual(result.seller_phone, "+380975554433")


if __name__ == "__main__":
    unittest.main()
