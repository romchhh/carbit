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

        listing = SimpleNamespace(
            id="olx_1",
            brand="BMW",
            model="X5",
            year=2022,
            mileage=15000,
            vin=None,
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

    async def test_soft_match_hit(self):
        from app.services.notifications.service import user_already_notified_for_car

        listing = SimpleNamespace(
            id="olx_2",
            brand="BMW",
            model="X5",
            year=2022,
            mileage=15000,
            vin=None,
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
            vin=None,
            title="BMW X5 xDrive",
            description=None,
        )

        db = AsyncMock()
        # family ids query
        family_result = SimpleNamespace(all=lambda: ["olx_2"])
        recent_result = SimpleNamespace(all=lambda: [other])

        async def scalars_side_effect(stmt):
            # first call family, second recent — approximate by call order
            if not hasattr(scalars_side_effect, "n"):
                scalars_side_effect.n = 0
            scalars_side_effect.n += 1
            return family_result if scalars_side_effect.n == 1 else recent_result

        db.scalars = AsyncMock(side_effect=scalars_side_effect)
        db.scalar = AsyncMock(return_value=None)

        self.assertTrue(await user_already_notified_for_car(db, "user-1", listing))


class CreateNotificationSkipTests(unittest.IsolatedAsyncioTestCase):
    async def test_skips_telegram_for_duplicate_mirror(self):
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

        send.assert_not_awaited()
        self.assertFalse(notif.sent_telegram)
        self.assertTrue(notif.payload.get("telegram_skipped_duplicate"))


if __name__ == "__main__":
    unittest.main()
