from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from datetime import datetime

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import ListingOut
from app.services.auto_ria.html_hydrate import (
    auto_ria_listing_url,
    batch_enrich_auto_ria_html,
    enrich_listing_from_html,
    parse_auto_ria_listing_id,
)


def _listing(**kwargs) -> ListingOut:
    base = dict(
        id="auto_ria_123",
        source="auto_ria",
        title="BMW X5",
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
        images=["https://cdn/cover.jpg"],
        url="https://auto.ria.com/uk/auto_bmw_x5_123.html",
        seller_type="private",
        price_history=[],
        is_duplicate=False,
        published_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
        found_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
    )
    base.update(kwargs)
    return ListingOut(**base)


class AutoRiaHtmlHydrateTests(unittest.IsolatedAsyncioTestCase):
    def test_auto_ria_listing_url_short_paths(self):
        self.assertEqual(auto_ria_listing_url(40307001), "https://auto.ria.com/auto/40307001.html")
        self.assertEqual(
            auto_ria_listing_url(2073874, is_new=True),
            "https://auto.ria.com/newauto/2073874.html",
        )

    def test_parse_auto_ria_listing_id(self):
        self.assertEqual(parse_auto_ria_listing_id("auto_ria_123"), (123, False))
        self.assertEqual(parse_auto_ria_listing_id("new_auto_ria_456"), (456, True))

    async def test_enrich_listing_from_html_uses_parser(self):
        listing = _listing()

        async def _enrich(car):
            car.photos = ["https://cdn/1.jpg", "https://cdn/2.jpg"]
            car.price_usd = 25000
            car.year = 2020

        with patch("app.services.auto_ria.html_hydrate.AutoRiaBetaClient") as client_cls:
            client = client_cls.return_value
            client.enrich_car = AsyncMock(side_effect=_enrich)

            result = await enrich_listing_from_html(
                url=listing.url,
                car_id=123,
                card=listing,
            )

        client.enrich_car.assert_called_once()
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result.images or []), 1)

    async def test_batch_enrich_builds_url_without_card(self):
        enriched = _listing(
            id="auto_ria_999",
            url="https://auto.ria.com/auto/999.html",
            images=["https://cdn/1.jpg", "https://cdn/2.jpg"],
        )

        with patch(
            "app.services.auto_ria.html_hydrate.enrich_listing_from_html",
            new_callable=AsyncMock,
            return_value=enriched,
        ) as enrich_mock:
            with patch("app.core.redis.get_redis", new_callable=AsyncMock) as redis_mock:
                redis = redis_mock.return_value
                redis.mget = AsyncMock(return_value=[None])
                redis.pipeline = lambda transaction=False: type(
                    "Pipe",
                    (),
                    {
                        "setex": lambda self, *a, **k: self,
                        "execute": AsyncMock(return_value=[]),
                    },
                )()

                result = await batch_enrich_auto_ria_html(
                    ["999"],
                    cache_prefix="test-ar:",
                    cache_ttl=60,
                    is_new=False,
                )

        enrich_mock.assert_called_once()
        self.assertEqual(enrich_mock.call_args.kwargs["url"], "https://auto.ria.com/auto/999.html")
        self.assertEqual(result["999"].id, "auto_ria_999")


if __name__ == "__main__":
    unittest.main()
