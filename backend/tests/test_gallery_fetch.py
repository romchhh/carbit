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

    async def test_fetch_auto_ria_uses_fotos_and_contact(self):
        fotos_payload = {
            "data": {
                "123": {
                    "1": {
                        "photo_id": 1,
                        "formats": {"f": "https://cdn.example.com/1f.jpg"},
                    },
                    "2": {
                        "photo_id": 2,
                        "formats": {"f": "https://cdn.example.com/2f.jpg"},
                    },
                }
            }
        }
        info_payload = {
            "autoData": {"autoId": 123},
            "dealer": {"name": "Test Dealer", "link": "/dealers/test"},
        }

        with patch("app.services.listings.gallery_fetch.AutoRiaClient") as client_cls:
            client = client_cls.return_value
            client.get_fotos = AsyncMock(return_value=fotos_payload)
            client.get_info = AsyncMock(return_value=info_payload)

            result = await fetch_auto_ria_gallery(
                listing_id="auto_ria_123",
                url="https://auto.ria.com/auto_123.html",
                current_images=["https://cdn.example.com/cover.jpg"],
            )

        self.assertEqual(len(result.images), 2)
        self.assertEqual(result.seller_name, "Test Dealer")

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
