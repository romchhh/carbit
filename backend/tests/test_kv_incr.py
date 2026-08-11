from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from storage.kv_store import SQLiteKV


class SQLiteIncrTests(unittest.IsolatedAsyncioTestCase):
    async def test_incr_starts_at_one_and_increments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "kv.db"
            kv = SQLiteKV(db_path)

            first = await kv.incr("counter")
            second = await kv.incr("counter")

            self.assertEqual(first, 1)
            self.assertEqual(second, 2)
            self.assertEqual(await kv.get("counter"), "2")

    async def test_incr_resets_after_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "kv.db"
            kv = SQLiteKV(db_path)

            await kv.incr("counter")
            with kv._connect() as conn:
                conn.execute(
                    "UPDATE kv SET expires_at = ? WHERE key = ?",
                    (0.0, "counter"),
                )

            again = await kv.incr("counter")
            self.assertEqual(again, 1)


class RateLimitIncrTests(unittest.IsolatedAsyncioTestCase):
    async def test_enforce_rate_limit_uses_incr(self) -> None:
        from app.services.rate_limit import enforce_rate_limit

        redis = AsyncMock()
        redis.incr = AsyncMock(side_effect=[1, 2, 3])
        redis.expire = AsyncMock()

        with patch("app.services.rate_limit.get_redis", return_value=redis):
            await enforce_rate_limit(key="test", limit=5, window_seconds=60)
            await enforce_rate_limit(key="test", limit=5, window_seconds=60)

        self.assertEqual(redis.incr.await_count, 2)
        redis.expire.assert_awaited_once_with("rate:test", 60)


if __name__ == "__main__":
    unittest.main()
