"""Дедуп Telegram-сповіщень по одному авто."""

from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.timezone import KYIV_TZ
from app.models.models import NotificationType


class AlreadyNotifiedTests(unittest.IsolatedAsyncioTestCase):
    async def test_family_id_hit(self):
        from app.services.notifications.service import user_already_notified_for_car

        vin = "WBA8E9C50HK123456"
        listing = SimpleNamespace(
            id="olx_1",
            brand="BMW",
            model="X5",
            year=2022,
            mileage=15000,
            vin=vin,
            duplicate_of="auto_ria_1",
            is_duplicate=True,
        )
        db = AsyncMock()
        # _duplicate_family_ids → scalar list, then Notification scalar
        db.scalars = AsyncMock(
            return_value=SimpleNamespace(all=lambda: ["olx_1", "auto_ria_1"])
        )
        db.scalar = AsyncMock(return_value="notif-1")

        self.assertTrue(await user_already_notified_for_car(db, "user-1", listing))

    async def test_duplicate_link_without_vin_is_not_blocked(self):
        from app.services.notifications.service import user_already_notified_for_car

        listing = SimpleNamespace(
            id="olx_1",
            vin=None,
            duplicate_of="auto_ria_1",
            is_duplicate=True,
        )
        db = AsyncMock()
        self.assertFalse(await user_already_notified_for_car(db, "user-1", listing))

    async def test_soft_match_hit(self):
        from app.services.notifications.service import user_already_notified_for_car

        vin = "WBA8E9C50HK123456"
        listing = SimpleNamespace(
            id="olx_2",
            brand="BMW",
            model="X5",
            year=2022,
            mileage=15000,
            vin=vin,
            duplicate_of=None,
            is_duplicate=False,
            title="BMW X5",
            description=None,
        )
        other = SimpleNamespace(
            id="olx_1",
            brand="BMW",
            model="X5",
            year=2022,
            mileage=15200,
            vin=vin,
            title="BMW X5 xDrive",
            description=None,
        )

        db = AsyncMock()
        family_result = SimpleNamespace(all=lambda: ["olx_2"])
        recent_result = SimpleNamespace(all=lambda: [other])

        async def scalars_side_effect(stmt):
            if not hasattr(scalars_side_effect, "n"):
                scalars_side_effect.n = 0
            scalars_side_effect.n += 1
            return family_result if scalars_side_effect.n == 1 else recent_result

        db.scalars = AsyncMock(side_effect=scalars_side_effect)
        db.scalar = AsyncMock(return_value=None)

        self.assertTrue(await user_already_notified_for_car(db, "user-1", listing))

    async def test_soft_match_without_vin_is_not_duplicate(self):
        from app.services.notifications.service import user_already_notified_for_car

        listing = SimpleNamespace(
            id="olx_2",
            brand="Zeekr",
            model="001",
            year=2025,
            mileage=5000,
            vin=None,
            duplicate_of=None,
            is_duplicate=False,
        )
        db = AsyncMock()
        db.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: ["olx_2"]))
        db.scalar = AsyncMock(return_value=None)

        self.assertFalse(await user_already_notified_for_car(db, "user-1", listing))


class CreateNotificationSkipTests(unittest.IsolatedAsyncioTestCase):
    async def test_sends_telegram_for_vin_mirror_with_cross_source_alert(self):
        from app.services.notifications.service import create_listing_notification

        listing = SimpleNamespace(
            id="olx_dup",
            source="olx",
            title="BMW X5",
            year=2022,
            mileage=15000,
            price=30000,
            currency="USD",
            region="Київ",
            fuel="Гібрид",
            transmission="Автомат",
            description=None,
            images=[],
            url="https://olx.ua/1",
            published_at=datetime(2026, 7, 15, 10, 0, tzinfo=KYIV_TZ),
            is_duplicate=True,
            duplicate_of="auto_ria_1",
            vin="WBA8E9C50HK123456",
            brand="BMW",
            model="X5",
        )
        user = SimpleNamespace(
            id="u1",
            telegram_connected=True,
            telegram_id="123",
        )
        search = SimpleNamespace(id="s1", name="BMW")

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        with patch(
            "app.services.notifications.service.telegram_client.send_listing_card",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ) as send:
            with patch(
                "app.services.notifications.service.build_cross_source_telegram_alert",
                new_callable=AsyncMock,
                return_value=("Це авто вже знайдено на AUTO.RIA. Ось оголошення з OLX.", "🔗"),
            ):
                with patch(
                    "app.services.notifications.service.format_display_price",
                    return_value="30 000 $",
                ):
                    notif = await create_listing_notification(
                        db, user, listing, search=search, send_telegram=True
                    )

        send.assert_awaited_once()
        self.assertTrue(notif.sent_telegram)
        self.assertEqual(send.await_args.kwargs.get("alert_emoji"), "🔗")
        self.assertIn("AUTO.RIA", send.await_args.kwargs.get("alert_line", ""))

    async def test_telegram_notification_includes_one_photo(self):
        from app.services.notifications.service import create_listing_notification

        from app.core.timezone import now_kyiv

        listing = SimpleNamespace(
            id="telegram_test_1",
            source="telegram",
            title="BMW X5",
            year=2022,
            mileage=15000,
            price=30000,
            currency="USD",
            region="Київ",
            fuel="Бензин",
            transmission="Автомат",
            description=None,
            images=[
                "/api/v1/telegram-media/ua_autobazar/1.jpg",
                "/api/v1/telegram-media/ua_autobazar/2.jpg",
            ],
            url="https://t.me/test/1",
            published_at=now_kyiv(),
            is_duplicate=False,
            duplicate_of=None,
            vin=None,
            brand="BMW",
            model="X5",
        )
        user = SimpleNamespace(
            id="u1",
            telegram_connected=True,
            telegram_id="123",
        )
        search = SimpleNamespace(id="s1", name="BMW")

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        with patch(
            "app.services.notifications.service.telegram_client.send_listing_card",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ) as send:
            with patch(
                "app.services.notifications.service.user_already_notified_for_car",
                new_callable=AsyncMock,
                return_value=False,
            ):
                with patch(
                    "app.services.notifications.service.format_display_price",
                    return_value="30 000 $",
                ):
                    notif = await create_listing_notification(
                        db, user, listing, search=search, send_telegram=True
                    )

        send.assert_awaited_once()
        payload = send.await_args.args[1]
        self.assertEqual(len(payload["images"]), 1)
        self.assertIn("/api/v1/telegram-media/", payload["images"][0])
        self.assertTrue(notif.sent_telegram)


if __name__ == "__main__":
    unittest.main()
