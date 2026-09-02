from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.services.meta.conversions import (
    build_purchase_event,
    build_purchase_event_id,
    meta_conversions_configured,
    send_meta_purchase_event,
)


class MetaConversionsTests(unittest.TestCase):
    def test_build_purchase_event_id_prefers_payment_id(self) -> None:
        self.assertEqual(build_purchase_event_id(order_id="ord1"), "purchase_ord1")
        self.assertEqual(
            build_purchase_event_id(order_id="ord1", payment_id="pay9"),
            "purchase_pay9",
        )

    def test_build_purchase_event_hashes_user_data(self) -> None:
        event = build_purchase_event(
            user_id="user-1",
            email="Test@Example.com",
            phone="+380 (67) 123-45-67",
            order_id="carbit_pro_abc",
            payment_id="12345",
            plan_id="pro",
            plan_name="Pro",
            amount=499.0,
            currency="uah",
            event_time=1_700_000_000,
        )
        self.assertEqual(event["event_name"], "Purchase")
        self.assertEqual(event["event_id"], "purchase_12345")
        self.assertEqual(event["custom_data"]["value"], 499.0)
        self.assertEqual(event["custom_data"]["currency"], "UAH")
        self.assertIn("em", event["user_data"])
        self.assertIn("ph", event["user_data"])
        self.assertEqual(len(event["user_data"]["em"][0]), 64)

    def test_meta_conversions_configured_requires_token(self) -> None:
        with patch("app.services.meta.conversions.settings") as settings:
            settings.META_PIXEL_ID = "1619297012895746"
            settings.META_CONVERSIONS_ACCESS_TOKEN = ""
            self.assertFalse(meta_conversions_configured())
            settings.META_CONVERSIONS_ACCESS_TOKEN = "token"
            self.assertTrue(meta_conversions_configured())


class MetaConversionsAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_meta_purchase_event_posts_to_graph(self) -> None:
        with patch("app.services.meta.conversions.meta_conversions_configured", return_value=True), patch(
            "app.services.meta.conversions.settings"
        ) as settings, patch("app.services.meta.conversions.httpx.AsyncClient") as client_cls:
            settings.META_PIXEL_ID = "1619297012895746"
            settings.META_CONVERSIONS_ACCESS_TOKEN = "secret"
            response = AsyncMock()
            response.status_code = 200
            response.text = '{"events_received":1}'
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.post = AsyncMock(return_value=response)
            client_cls.return_value = client

            ok = await send_meta_purchase_event(
                user_id="u1",
                email="a@b.com",
                phone=None,
                order_id="ord",
                payment_id="pay",
                plan_id="lite",
                plan_name="Lite",
                amount=199,
                currency="UAH",
            )

        self.assertTrue(ok)
        client.post.assert_awaited_once()
        url = client.post.await_args.args[0]
        self.assertIn("1619297012895746", url)
        payload = client.post.await_args.kwargs["json"]
        self.assertEqual(payload["data"][0]["event_name"], "Purchase")


if __name__ == "__main__":
    unittest.main()
