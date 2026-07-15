"""Lazy hydrate: visible-page batches for RIA / OLX / Telegram."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.core.timezone import now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.search import search_endpoint


def _listing(auto_id: str, *, source: str = "auto_ria") -> ListingOut:
    prefix = {"auto_ria": "auto_ria_", "olx": "olx_", "telegram": "telegram_"}.get(source, f"{source}_")
    return ListingOut(
        id=f"{prefix}{auto_id}",
        source=source,
        title=f"Car {auto_id}",
        brand="Zeekr",
        model="001",
        year=2024,
        price=1000 + int(auto_id) if str(auto_id).isdigit() else 1000,
        currency="USD",
        mileage=1000,
        fuel="Електро",
        transmission="",
        region="Київ",
        description=None,
        images=["https://cdn.example/a.jpg"],
        url=f"https://example.com/{auto_id}",
        seller_type="private",
        price_history=[],
        is_duplicate=False,
        published_at=now_kyiv(),
        found_at=now_kyiv(),
    )


def _empty_pool(**overrides):
    base = {
        "items": [],
        "pending_ria_ids": [str(i) for i in range(1, 31)],
        "ria_fetched": 0,
        "olx_next_page": 1,
        "olx_fetched": 0,
        "olx_exhausted": False,
        "olx_total": 0,
        "tg_enabled": True,
        "tg_next_page": 1,
        "tg_fetched": 0,
        "tg_exhausted": False,
        "tg_total": 0,
        "market_ria": 30,
        "market_total": 30,
        "partial": False,
        "sources": [
            {"source": "AUTO.RIA", "item_count": 30, "error": None, "pending": False},
            {"source": "OLX", "item_count": 0, "error": None, "pending": False},
            {"source": "Telegram", "item_count": 0, "error": None, "pending": False},
        ],
    }
    base.update(overrides)
    return base


class LazyHydrateWindowTests(unittest.IsolatedAsyncioTestCase):
    async def test_page1_pulls_one_batch_per_source(self):
        pool = _empty_pool()
        hydrate_ria = AsyncMock(
            side_effect=lambda ids, sort_by="newest": [_listing(i) for i in ids]
        )
        fetch_olx = AsyncMock(
            return_value=([_listing(str(i), source="olx") for i in range(1, 11)], False)
        )
        fetch_tg = AsyncMock(
            return_value=([_listing(str(i), source="telegram") for i in range(1, 11)], 40, False)
        )

        with (
            patch.object(search_endpoint, "hydrate_auto_ria_ids", hydrate_ria),
            patch.object(search_endpoint, "_fetch_olx_batch", fetch_olx),
            patch.object(search_endpoint, "_fetch_tg_batch", fetch_tg),
            patch.object(search_endpoint, "set_live_pool", AsyncMock()),
        ):
            out = await search_endpoint._ensure_pool_hydrated(
                pool,
                filters=SearchFilters(brand="Zeekr", model="001"),
                sort_by="newest",
                page=1,
                per_page=10,
            )

        self.assertEqual(hydrate_ria.await_count, 1)
        self.assertEqual(fetch_olx.await_count, 1)
        self.assertEqual(fetch_tg.await_count, 1)
        self.assertEqual(out["ria_fetched"], 10)
        self.assertEqual(out["olx_fetched"], 10)
        self.assertEqual(out["tg_fetched"], 10)
        self.assertEqual(len(out["pending_ria_ids"]), 20)

    async def test_page2_advances_all_cursors(self):
        items = [_listing(str(i)).model_dump(mode="json") for i in range(1, 11)]
        items += [_listing(str(i), source="olx").model_dump(mode="json") for i in range(1, 11)]
        items += [_listing(str(i), source="telegram").model_dump(mode="json") for i in range(1, 11)]
        pool = _empty_pool(
            items=items,
            pending_ria_ids=[str(i) for i in range(11, 31)],
            ria_fetched=10,
            olx_next_page=2,
            olx_fetched=10,
            tg_next_page=2,
            tg_fetched=10,
            tg_total=40,
        )
        hydrate_ria = AsyncMock(
            side_effect=lambda ids, sort_by="newest": [_listing(i) for i in ids]
        )
        fetch_olx = AsyncMock(
            return_value=([_listing(str(i), source="olx") for i in range(11, 21)], False)
        )
        fetch_tg = AsyncMock(
            return_value=([_listing(str(i), source="telegram") for i in range(11, 21)], 40, False)
        )

        with (
            patch.object(search_endpoint, "hydrate_auto_ria_ids", hydrate_ria),
            patch.object(search_endpoint, "_fetch_olx_batch", fetch_olx),
            patch.object(search_endpoint, "_fetch_tg_batch", fetch_tg),
            patch.object(search_endpoint, "set_live_pool", AsyncMock()),
        ):
            out = await search_endpoint._ensure_pool_hydrated(
                pool,
                filters=SearchFilters(brand="Zeekr", model="001"),
                sort_by="newest",
                page=2,
                per_page=10,
            )

        self.assertEqual(out["ria_fetched"], 20)
        self.assertEqual(out["olx_fetched"], 20)
        self.assertEqual(out["tg_fetched"], 20)
        self.assertEqual(out["olx_next_page"], 3)
        self.assertEqual(out["tg_next_page"], 3)
        hydrate_ria.assert_awaited_once()
        fetch_olx.assert_awaited_once()
        fetch_tg.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
