from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.services.admin.visit_stats import (
    build_traffic_report,
    country_label,
    is_bot_user_agent,
    normalize_path,
    path_label,
    record_visit,
)


class VisitStatsHelpersTests(unittest.TestCase):
    def test_normalize_path(self):
        self.assertEqual(normalize_path("/pricing/"), "/pricing")
        self.assertEqual(normalize_path("app/search?q=1"), "/app/search")
        self.assertEqual(normalize_path(""), "/")

    def test_path_label(self):
        self.assertEqual(path_label("/"), "Головна")
        self.assertEqual(path_label("/app/listing/abc"), "Оголошення (шеринг)")

    def test_country_label(self):
        self.assertEqual(country_label("ua"), "Україна")
        self.assertEqual(country_label("ZZ"), "ZZ")

    def test_bot_detection(self):
        self.assertTrue(is_bot_user_agent("Mozilla/5.0 Googlebot/2.1"))
        self.assertFalse(is_bot_user_agent("Mozilla/5.0 Chrome/120"))


class VisitStatsRecordTests(unittest.IsolatedAsyncioTestCase):
    async def test_record_visit_increments_counters(self):
        stored_hashes: dict[str, dict[str, int]] = {}
        stored_sets: dict[str, float] = {}

        redis = AsyncMock()

        async def hincrby(key: str, field: str, amount: int = 1) -> int:
            stored_hashes.setdefault(key, {})
            stored_hashes[key][field] = stored_hashes[key].get(field, 0) + amount
            return stored_hashes[key][field]

        async def hgetall(key: str) -> dict[str, str]:
            return {k: str(v) for k, v in stored_hashes.get(key, {}).items()}

        async def exists(key: str) -> int:
            return 1 if key in stored_sets else 0

        async def setex(key: str, ttl: int, value: str) -> None:
            stored_sets[key] = ttl

        async def expire(key: str, ttl: int) -> None:
            _ = (key, ttl)

        async def zadd(key: str, mapping: dict[str, float]) -> None:
            stored_sets.update({f"z:{k}": v for k, v in mapping.items()})

        async def zremrangebyscore(key: str, min_score: float, max_score: float) -> int:
            _ = (key, min_score, max_score)
            return 0

        async def zcard(key: str) -> int:
            return len([k for k in stored_sets if k.startswith("z:")])

        redis.hincrby = AsyncMock(side_effect=hincrby)
        redis.hgetall = AsyncMock(side_effect=hgetall)
        redis.exists = AsyncMock(side_effect=exists)
        redis.setex = AsyncMock(side_effect=setex)
        redis.expire = AsyncMock(side_effect=expire)
        redis.zadd = AsyncMock(side_effect=zadd)
        redis.zremrangebyscore = AsyncMock(side_effect=zremrangebyscore)
        redis.zcard = AsyncMock(side_effect=zcard)

        with patch("app.services.admin.visit_stats.get_redis", AsyncMock(return_value=redis)):
            await record_visit(
                path="/pricing",
                visitor_id="visitor-12345678",
                country="UA",
                user_agent="Mozilla/5.0",
                device="desktop",
            )
            report = await build_traffic_report(hours=6, days=3)

        self.assertGreaterEqual(report["today_total"], 1)
        self.assertGreaterEqual(report["period_total"], 1)
        self.assertTrue(any(row["code"] == "UA" for row in report["countries"]))
        self.assertTrue(any(row["path"] == "/pricing" for row in report["top_pages"]))

    async def test_record_visit_skips_admin_and_bots(self):
        redis = AsyncMock()
        with patch("app.services.admin.visit_stats.get_redis", AsyncMock(return_value=redis)):
            await record_visit(
                path="/admin/traffic",
                visitor_id="visitor-12345678",
                country="UA",
                user_agent="Googlebot/2.1",
            )
            await record_visit(
                path="/",
                visitor_id="visitor-12345678",
                country="UA",
                user_agent="Googlebot/2.1",
            )
        redis.hincrby.assert_not_called()


if __name__ == "__main__":
    unittest.main()
