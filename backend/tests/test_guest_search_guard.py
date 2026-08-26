"""Тести захисту гостьового пошуку."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.search.guest_guard import (
    enforce_guest_search_protection,
    verify_guest_internal_secret,
)


class GuestGuardUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocks_bot_user_agent(self):
        class FakeRequest:
            headers = {"user-agent": "Googlebot/2.1"}

        with self.assertRaises(HTTPException) as ctx:
            await enforce_guest_search_protection(FakeRequest())  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.status_code, 403)

    def test_rejects_missing_internal_secret(self):
        with self.assertRaises(HTTPException) as ctx:
            verify_guest_internal_secret(None)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_accepts_valid_internal_secret(self):
        verify_guest_internal_secret(settings.INTERNAL_API_SECRET)


class GuestLiveSearchApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_guest_live_search_requires_internal_secret(self):
        res = self.client.post("/api/v1/searches/live/guest", json={"brand": "Toyota"})
        self.assertEqual(res.status_code, 403)

    @patch("app.api.v1.searches.run_live_search", new_callable=AsyncMock)
    @patch("app.api.v1.searches.enforce_guest_search_limit", new_callable=AsyncMock, return_value=2)
    def test_guest_live_search_with_secret(self, _limit_mock, search_mock):
        from app.schemas.schemas import PaginatedListings

        search_mock.return_value = PaginatedListings(
            items=[],
            total=0,
            page=1,
            per_page=20,
            pages=0,
        )
        res = self.client.post(
            "/api/v1/searches/live/guest",
            json={"brand": "Toyota"},
            headers={
                "X-Internal-Secret": settings.INTERNAL_API_SECRET,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            },
        )
        self.assertIn(res.status_code, {200, 429})


if __name__ == "__main__":
    unittest.main()
