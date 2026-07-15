"""Tests for AUTO.RIA per-auto_id detail cache."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.services.auto_ria import detail_cache
from app.services.auto_ria.mapper import info_to_listing


def _sample_info(auto_id: str = "123") -> dict:
    return {
        "autoData": {"autoId": int(auto_id) if auto_id.isdigit() else 0, "year": 2024, "raceInt": 5},
        "title": "Zeekr 001",
        "markName": "Zeekr",
        "modelName": "001",
        "USD": 45_000,
        "UAH": 1_800_000,
        "linkToView": f"/auto_zeekr_001_{auto_id}.html",
        "addDate": "2026-07-10 12:00:00",
        "photoData": {"seoLinkF": "https://cdn.example/cover.jpg"},
        "stateData": {"name": "Київ"},
    }


class DetailCacheResolveTests(unittest.IsolatedAsyncioTestCase):
    async def test_kv_hit_skips_api(self):
        info = _sample_info("99")
        fetch_info = AsyncMock(side_effect=AssertionError("API must not be called"))

        with (
            patch.object(detail_cache, "get_many_infos", AsyncMock(return_value={"99": info})),
            patch.object(detail_cache, "get_fresh_listings_from_db", AsyncMock(return_value={})),
            patch.object(detail_cache, "set_info", AsyncMock()),
        ):
            items = await detail_cache.resolve_listings(["99"], fetch_info=fetch_info)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, "auto_ria_99")
        self.assertEqual(items[0].brand, "Zeekr")
        fetch_info.assert_not_called()

    async def test_api_miss_writes_cache(self):
        info = _sample_info("77")
        fetch_info = AsyncMock(return_value=info)
        set_info = AsyncMock()

        with (
            patch.object(detail_cache, "get_many_infos", AsyncMock(return_value={})),
            patch.object(detail_cache, "get_fresh_listings_from_db", AsyncMock(return_value={})),
            patch.object(detail_cache, "set_info", set_info),
        ):
            items = await detail_cache.resolve_listings(["77"], fetch_info=fetch_info)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, "auto_ria_77")
        fetch_info.assert_awaited_once_with("77")
        set_info.assert_awaited_once()
        self.assertEqual(set_info.await_args.args[0], "77")

    async def test_db_hit_with_images_skips_api(self):
        info = _sample_info("55")
        listing = info_to_listing(info, fotos=None)
        listing.images = ["https://cdn.example/a.jpg"]
        fetch_info = AsyncMock(side_effect=AssertionError("API must not be called"))

        with (
            patch.object(detail_cache, "get_many_infos", AsyncMock(return_value={})),
            patch.object(
                detail_cache,
                "get_fresh_listings_from_db",
                AsyncMock(return_value={"55": listing}),
            ),
            patch.object(detail_cache, "set_info", AsyncMock()),
        ):
            items = await detail_cache.resolve_listings(["55"], fetch_info=fetch_info)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].images, ["https://cdn.example/a.jpg"])
        fetch_info.assert_not_called()

    def test_ttl_is_about_two_weeks(self):
        self.assertGreaterEqual(detail_cache.CACHE_TTL_SECONDS, 60 * 60 * 24 * 7)
        self.assertLessEqual(detail_cache.CACHE_TTL_SECONDS, 60 * 60 * 24 * 14)


if __name__ == "__main__":
    unittest.main()
