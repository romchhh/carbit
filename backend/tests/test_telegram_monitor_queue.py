"""Черга моніторингу в Telegram не повинна глухнути на ліміті чи битому URL."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.notifications.service import (
    TELEGRAM_GIVE_UP_ATTEMPTS,
    note_telegram_delivery_failure,
)
from app.services.telegram.client import (
    TelegramClient,
    TelegramPermanentError,
    TelegramRateLimit,
    TelegramTransientError,
    telegram_button_url,
    telegram_failure_is_permanent,
)


class TelegramButtonUrlTests(unittest.TestCase):
    def test_accepts_http(self):
        self.assertEqual(telegram_button_url("https://carbit.info/x"), "https://carbit.info/x")

    def test_rejects_relative_and_empty(self):
        self.assertIsNone(telegram_button_url("/app/listing/1"))
        self.assertIsNone(telegram_button_url(""))
        self.assertIsNone(telegram_button_url(None))


class TelegramFailureBackoffTests(unittest.TestCase):
    def test_attempts_grow_until_give_up(self):
        note = SimpleNamespace(payload={})
        for expected in range(1, TELEGRAM_GIVE_UP_ATTEMPTS + 1):
            self.assertEqual(note_telegram_delivery_failure(note), expected)
        self.assertEqual(note.payload["telegram_attempts"], TELEGRAM_GIVE_UP_ATTEMPTS)


class TelegramFailureKindTests(unittest.TestCase):
    def test_blocked_chat_is_permanent(self):
        self.assertTrue(telegram_failure_is_permanent("Forbidden: bot was blocked by the user"))
        self.assertTrue(telegram_failure_is_permanent("Bad Request: chat not found"))

    def test_bad_photo_is_not_permanent(self):
        self.assertFalse(telegram_failure_is_permanent("Bad Request: failed to get HTTP URL content"))


class ListingCardMarkupTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_urls_still_send_text(self):
        client = TelegramClient(token="test-token")
        client._call = AsyncMock(return_value={"ok": True, "result": {"message_id": 1}})
        with patch("app.services.telegram.client.settings") as cfg:
            cfg.FRONTEND_URL = ""
            result = await client.send_listing_card(
                1,
                {"title": "BMW <X5>", "url": "not-a-url", "images": []},
                "Пошук",
                search_id="search-1",
                listing_id="listing-1",
            )
        self.assertTrue(result.get("ok"))
        payload = client._call.await_args.args[1]
        self.assertIn("BMW &lt;X5&gt;", payload["text"])
        buttons = payload["reply_markup"]["inline_keyboard"]
        self.assertEqual(buttons[0][0]["callback_data"], "mon:ask:search-1")


def _queue_row(user_id: str, listing_id: str):
    return (
        SimpleNamespace(is_new=True, notified_at=None, search_id="s", listing_id=listing_id),
        SimpleNamespace(id="s", new_count=1),
        SimpleNamespace(id=user_id, telegram_connected=True, telegram_id="100"),
        SimpleNamespace(id=listing_id),
    )


class MonitorQueueIsolationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.note = SimpleNamespace(sent_telegram=False, payload={})
        self.db = AsyncMock()
        self.db.scalar = AsyncMock(return_value=self.note)

    def _patches(self, attempt):
        return (
            patch("app.services.notifications.service.listing_matches_search_query", return_value=True),
            patch("app.services.notifications.service.flush_session", new_callable=AsyncMock),
            patch(
                "app.services.notifications.service.build_cross_source_telegram_alert",
                new_callable=AsyncMock,
                return_value=(None, "🚗"),
            ),
            patch(
                "app.services.notifications.service._attempt_listing_match_telegram",
                side_effect=attempt,
            ),
        )

    async def _deliver(self, rows, attempt):
        from app.services.notifications.service import _deliver_monitor_rows

        contexts = self._patches(attempt)
        for ctx in contexts:
            ctx.start()
        try:
            return await _deliver_monitor_rows(self.db, rows, max_hours=24, persist_each=False)
        finally:
            for ctx in reversed(contexts):
                ctx.stop()

    async def test_rejected_card_does_not_stop_the_next_car(self):
        calls = {"n": 0}

        async def attempt(*_args, **_kwargs):
            calls["n"] += 1
            return calls["n"] > 1

        first, second = _queue_row("u", "a"), _queue_row("u", "b")
        delivered = await self._deliver([first, second], attempt)
        self.assertEqual(delivered, 1)
        self.assertEqual(calls["n"], 2)
        self.assertIsNone(first[0].notified_at)
        self.assertTrue(first[0].is_new)
        self.assertIsNotNone(second[0].notified_at)

    async def test_rate_limit_stops_the_batch(self):
        calls = {"n": 0}

        async def attempt(*_args, **_kwargs):
            calls["n"] += 1
            raise TelegramRateLimit(9)

        delivered = await self._deliver([_queue_row("u", "a"), _queue_row("u", "b")], attempt)
        self.assertEqual(delivered, 0)
        self.assertEqual(calls["n"], 1)
        self.assertEqual(self.note.payload.get("telegram_attempts", 0), 0)

    async def test_blocked_user_does_not_block_someone_else(self):
        calls = {"users": []}

        async def attempt(_db, user, *_args, **_kwargs):
            calls["users"].append(user.id)
            if user.id == "blocked":
                raise TelegramPermanentError("bot was blocked by the user")
            return True

        delivered = await self._deliver(
            [
                _queue_row("blocked", "a"),
                _queue_row("blocked", "b"),
                _queue_row("ok", "c"),
            ],
            attempt,
        )
        self.assertEqual(delivered, 1)
        self.assertEqual(calls["users"], ["blocked", "ok"])

    async def test_large_backlog_survives_one_bad_card_and_rate_limit(self):
        rows = [_queue_row("u", f"car-{index}") for index in range(40)]
        calls = {"n": 0}

        async def attempt(*_args, **_kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return False
            if calls["n"] == 11:
                raise TelegramRateLimit(5)
            return True

        first_pass = await self._deliver(rows, attempt)
        self.assertEqual(first_pass, 9)
        self.assertEqual(calls["n"], 11)
        self.assertTrue(rows[0][0].is_new)
        self.assertIsNone(rows[0][0].notified_at)
        self.assertTrue(all(row[0].notified_at is not None for row in rows[1:10]))
        self.assertTrue(all(row[0].notified_at is None for row in rows[10:]))

        async def finish(*_args, **_kwargs):
            return True

        second_pass = await self._deliver(rows[10:], finish)
        self.assertEqual(second_pass, 30)
        self.assertTrue(all(row[0].notified_at is not None for row in rows[10:]))

    async def test_transient_errors_pause_without_dropping_cars(self):
        calls = {"n": 0}

        async def attempt(*_args, **_kwargs):
            calls["n"] += 1
            raise TelegramTransientError("timeout")

        rows = [_queue_row("u", "a"), _queue_row("u", "b"), _queue_row("u", "c"), _queue_row("u", "d")]
        delivered = await self._deliver(rows, attempt)
        self.assertEqual(delivered, 0)
        self.assertEqual(calls["n"], 3)
        self.assertTrue(all(row[0].is_new for row in rows))
        self.assertEqual(self.note.payload.get("telegram_attempts", 0), 0)


class TelegramRateLimitRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_still_429_raises_so_queue_stops(self):
        from app.services.telegram.client import TelegramClient

        client = TelegramClient(token="test-token")
        response = MagicMock()
        response.status_code = 429
        response.json.return_value = {"parameters": {"retry_after": 1}}
        http = AsyncMock()
        http.post = AsyncMock(return_value=response)

        with patch("app.services.telegram.client.asyncio.sleep", new_callable=AsyncMock):
            with self.assertRaises(TelegramRateLimit):
                await client._post_with_retry(http, "sendMessage", json={})
        self.assertEqual(http.post.await_count, 3)


if __name__ == "__main__":
    unittest.main()
