import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.schemas.schemas import ListingOut, SearchFilters
from app.services.auto_ria.discover import AutoRiaDiscoverResult, discover_auto_ria
from app.services.auto_ria.html_merge import listing_numeric_id, merge_html_card_with_api
from app.services.auto_ria_beta.mapper import car_to_listing
from app.services.auto_ria_beta.parser import ScrapedCar
from app.services.auto_ria_beta.service import AutoRiaBetaBatch
from app.services.search.multi_source import _listing_to_slot, normalize_sources


def _html_listing() -> ListingOut:
    return car_to_listing(
        ScrapedCar(
            car_id=40307001,
            url="https://auto.ria.com/uk/auto_byd_song-plus_40307001.html",
            brand="BYD",
            model="Song Plus",
            year=2023,
            price_usd=25000,
            plate="AB 7875 YA",
            details={"usa_import": False, "had_accident": True},
            photos=["https://cdn.riastatic.com/card.jpg"],
        ),
        brand_hint="BYD",
    )


def _api_listing() -> ListingOut:
    return ListingOut(
        id="auto_ria_40307001",
        source="auto_ria",
        title="BYD Song Plus",
        brand="BYD",
        model="Song Plus",
        year=2023,
        price=24900,
        currency="USD",
        mileage=52000,
        fuel="Електро",
        transmission="Автомат",
        region="Київ",
        description=None,
        images=[],
        url="https://auto.ria.com/uk/auto_byd_song-plus_40307001.html",
        seller_type="private",
        vin="LGXCE4CB3R0672315",
        published_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        found_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        source_data={"VIN": "LGXCE4CB3R0672315", "autoData": {"year": 2023}},
        price_history=[],
        is_duplicate=False,
    )


class AutoRiaHtmlMergeTests(unittest.TestCase):
    def test_html_card_uses_paid_auto_ria_identity(self):
        listing = _html_listing()
        self.assertEqual(listing.id, "auto_ria_40307001")
        self.assertEqual(listing.source, "auto_ria")
        self.assertEqual(listing.source_data["html_search"]["parser"], "html")
        self.assertEqual(listing_numeric_id(listing), "40307001")

    def test_html_card_slot_is_paid_stub_with_card_body(self):
        slot = _listing_to_slot(_html_listing())
        self.assertEqual(slot["s"], "r")
        self.assertEqual(slot["i"], "40307001")
        self.assertEqual(slot["d"]["id"], "auto_ria_40307001")
        self.assertEqual(slot["d"]["source"], "auto_ria")

    def test_merge_keeps_api_vin_and_html_badges_and_photo(self):
        merged = merge_html_card_with_api(_html_listing(), _api_listing())
        self.assertEqual(merged.vin, "LGXCE4CB3R0672315")
        self.assertEqual(merged.plate, "AB 7875 YA")
        self.assertEqual(merged.images, ["https://cdn.riastatic.com/card.jpg"])
        self.assertEqual(merged.source_data["html_search"]["parser"], "html")
        self.assertTrue(merged.had_accident)
        self.assertFalse(merged.usa_import)
        self.assertEqual(merged.published_at, _api_listing().published_at)

    def test_normalize_sources_aliases_test_beta_to_auto_ria(self):
        self.assertEqual(normalize_sources(["auto_ria_beta"]), ["auto_ria"])
        self.assertEqual(normalize_sources(["auto_ria", "AUTO.RIA test beta"]), ["auto_ria"])

    def test_normalize_sources_lubeavto_aliases(self):
        self.assertEqual(normalize_sources(["Любе Авто"]), ["lubeavto"])
        self.assertEqual(normalize_sources(["любе авто"]), ["lubeavto"])
        self.assertEqual(normalize_sources(["lubeavto"]), ["lubeavto"])


class AutoRiaDiscoverTests(unittest.IsolatedAsyncioTestCase):
    async def test_discover_falls_back_to_api_when_html_fails(self):
        filters = SearchFilters(brand="BYD")
        with (
            patch(
                "app.services.auto_ria.discover.fetch_auto_ria_beta_batch",
                new=AsyncMock(side_effect=RuntimeError("html down")),
            ),
            patch(
                "app.services.auto_ria.discover._fallback_api",
                new=AsyncMock(
                    return_value=AutoRiaDiscoverResult(
                        ids=["111"],
                        market_total=1,
                        fallback=True,
                        error="HTML-парсер: html down. Перемкнуто на API.",
                    )
                ),
            ) as fallback,
        ):
            result = await discover_auto_ria(filters, sort_by="newest")

        self.assertTrue(result.fallback)
        self.assertEqual(result.ids, ["111"])
        self.assertIn("Перемкнуто на API", result.error or "")
        fallback.assert_awaited_once()

    async def test_discover_uses_html_cards_when_parser_works(self):
        listing = _html_listing()
        batch = AutoRiaBetaBatch(
            listings=[listing],
            market_total=87,
            next_html_page=1,
            exhausted=False,
        )
        filters = SearchFilters(brand="BYD")
        with patch(
            "app.services.auto_ria.discover.fetch_auto_ria_beta_batch",
            new=AsyncMock(return_value=batch),
        ):
            result = await discover_auto_ria(filters, sort_by="newest")

        self.assertFalse(result.fallback)
        self.assertIsNone(result.error)
        self.assertEqual(result.ids, ["40307001"])
        self.assertEqual(result.market_total, 87)
        self.assertEqual(result.cards["40307001"].id, "auto_ria_40307001")
        self.assertEqual(result.html_cursor, {"next_html_page": 1, "exhausted": False})


class AutoRiaHtmlRaceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        from app.services.auto_ria_beta import client as ar

        ar._html_route = None

    async def test_html_race_does_not_wait_for_slower_leg(self):
        import time
        from types import SimpleNamespace

        from app.services.auto_ria_beta import client as ar

        ar._html_route = None
        direct = SimpleNamespace(name="direct")
        proxy = SimpleNamespace(name="proxy")

        async def fetch(client, url, params):
            if client is direct:
                await asyncio.sleep(0.25)
                return SimpleNamespace(status_code=200, text="direct")
            return SimpleNamespace(status_code=200, text="proxy")

        with (
            patch.object(ar, "_fetch_html", new=fetch),
            patch.object(ar, "proxy_configured", return_value=True),
            patch.object(ar, "_get_direct_client", new=AsyncMock(return_value=direct)),
            patch.object(ar, "_get_proxy_client", new=AsyncMock(return_value=proxy)),
        ):
            started = time.monotonic()
            response = await ar._get_html("https://auto.ria.com/uk/search/")
            elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.2)
        self.assertEqual(response.text, "proxy")
        self.assertEqual(ar._html_route, "proxy")

    async def test_html_race_does_not_wait_for_proxy_setup(self):
        import time
        from types import SimpleNamespace

        from app.services.auto_ria_beta import client as ar

        ar._html_route = None
        direct = SimpleNamespace(name="direct")
        proxy = SimpleNamespace(name="proxy")

        async def fetch(client, url, params):
            return SimpleNamespace(status_code=200, text=client.name)

        async def slow_proxy_client():
            await asyncio.sleep(0.25)
            return proxy

        with (
            patch.object(ar, "_fetch_html", new=fetch),
            patch.object(ar, "proxy_configured", return_value=True),
            patch.object(ar, "_get_direct_client", new=AsyncMock(return_value=direct)),
            patch.object(ar, "_get_proxy_client", new=slow_proxy_client),
        ):
            started = time.monotonic()
            response = await ar._get_html("https://auto.ria.com/uk/search/")
            elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.2)
        self.assertEqual(response.text, "direct")
        self.assertEqual(ar._html_route, "direct")
