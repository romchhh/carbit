"""Auth: Bearer + cookie fallback."""

from __future__ import annotations

import unittest
from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.auth_cookies import AUTH_COOKIE_NAME
from app.core.security import create_access_token
from app.main import app


class AuthCookieFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_cookie_alone_invalid_is_invalid_token(self):
        res = self.client.get("/api/v1/auth/me", cookies={AUTH_COOKIE_NAME: "not-a-jwt"})
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Invalid token")

    def test_stale_bearer_falls_back_to_cookie(self):
        good = create_access_token("user-test-id", expires_delta=timedelta(hours=1))
        res = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer totally-invalid"},
            cookies={AUTH_COOKIE_NAME: good},
        )
        # User may not exist in DB → 404, але не 401 Invalid token
        self.assertNotEqual(res.json().get("detail"), "Invalid token")
        self.assertNotEqual(res.json().get("detail"), "Not authenticated")
        self.assertIn(res.status_code, (200, 404))


if __name__ == "__main__":
    unittest.main()
