from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.services.auto_ria.details import extract_image_urls
from app.services.auto_ria.lazy_photos import auto_ria_needs_gallery


class AutoRiaLazyPhotosTests(unittest.TestCase):
    def test_cover_from_info_without_fotos(self):
        info = {
            "autoData": {"autoId": 123},
            "photoData": {"seoLinkF": "https://cdn.example.com/1f.jpg"},
        }
        urls = extract_image_urls(info, None)
        self.assertEqual(urls, ["https://cdn.example.com/1f.jpg"])

    def test_needs_gallery_with_single_cover(self):
        self.assertTrue(
            auto_ria_needs_gallery("auto_ria_123", images=["https://cdn/x.jpg"])
        )

    def test_no_gallery_needed_when_many_images(self):
        self.assertFalse(
            auto_ria_needs_gallery(
                "auto_ria_123",
                images=["https://a/1.jpg", "https://a/2.jpg"],
            )
        )

    def test_search_hydrate_skips_fotos_endpoint(self):
        import asyncio

        from app.services.auto_ria.service import _search_auto_ria_body
        from app.schemas.schemas import SearchFilters

        mock_info = {
            "autoData": {"autoId": 999, "year": 2020, "raceInt": 50},
            "markName": "BMW",
            "modelName": "X5",
            "title": "BMW X5",
            "linkToView": "/auto/999.html",
            "photoData": {"seoLinkF": "https://cdn/cover.jpg"},
            "USD": 25000,
        }

        with patch("app.services.auto_ria.service.AutoRiaClient") as client_cls:
            client = client_cls.return_value
            client.get_info = AsyncMock(return_value=mock_info)
            client.get_fotos = AsyncMock()
            client.search = AsyncMock(
                return_value={"result": {"search_result": {"count": 1, "ids": [999]}}}
            )
            with patch(
                "app.services.auto_ria.service.filters_to_search_params",
                new_callable=AsyncMock,
                return_value={},
            ):
                result = asyncio.run(
                    _search_auto_ria_body(SearchFilters(brand="BMW"), page=1, per_page=1)
                )

        client.get_fotos.assert_not_called()
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].images, ["https://cdn/cover.jpg"])


if __name__ == "__main__":
    unittest.main()
