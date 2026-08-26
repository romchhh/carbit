"""API smoke: app boots, health, docs gated, billing gate."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.main import app


class ApiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn(body.get("status"), {"ok", "degraded"})
        self.assertIn("database", body)
        self.assertIn("kv", body)

    def test_subscribe_requires_auth(self):
        res = self.client.post("/api/v1/billing/subscribe", json={"plan": "pro"})
        self.assertEqual(res.status_code, 401)

    def test_live_search_requires_auth(self):
        res = self.client.post("/api/v1/searches/live", json={})
        self.assertEqual(res.status_code, 401)

    def test_guest_live_search_no_auth(self):
        res = self.client.post("/api/v1/searches/live/guest", json={"brand": "Toyota"})
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
