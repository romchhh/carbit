"""Тести ліміту пристроїв / сесій."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.billing.plans import effective_devices_limit, get_plan


class DevicesLimitTests(unittest.TestCase):
    def test_plan_devices_limits(self):
        self.assertEqual(get_plan("free")["devices_limit"], 1)
        self.assertEqual(get_plan("lite")["devices_limit"], 2)
        self.assertEqual(get_plan("standard")["devices_limit"], 6)
        self.assertEqual(get_plan("pro")["devices_limit"], 12)


class SessionRegisterTests(unittest.IsolatedAsyncioTestCase):
    async def test_free_plan_revokes_old_session_on_new_login(self):
        from app.services.auth.sessions import is_session_active, register_session

        user = SimpleNamespace(id="user-1")

        fake_redis = AsyncMock()
        store: dict[str, object] = {}

        async def zadd(key, mapping):
            z = store.setdefault(key, {})
            z.update(mapping)

        async def zcard(key):
            return len(store.get(key, {}))

        async def zrange(key, start, end):
            z = store.get(key, {})
            items = sorted(z.items(), key=lambda x: x[1])
            return [k for k, _ in items[start : end + 1]]

        async def zrem(key, *members):
            z = store.get(key, {})
            for m in members:
                z.pop(m, None)

        async def setex(key, ttl, val):
            store[key] = val

        async def delete(key):
            store.pop(key, None)

        async def expire(key, ttl):
            return True

        async def exists(key):
            return 1 if key in store else 0

        fake_redis.zadd.side_effect = zadd
        fake_redis.zcard.side_effect = zcard
        fake_redis.zrange.side_effect = zrange
        fake_redis.zrem.side_effect = zrem
        fake_redis.setex.side_effect = setex
        fake_redis.delete.side_effect = delete
        fake_redis.expire.side_effect = expire
        fake_redis.exists.side_effect = exists

        with patch("app.services.auth.sessions.get_redis", AsyncMock(return_value=fake_redis)):
            with patch("app.services.auth.sessions.effective_devices_limit", return_value=1):
                await register_session(user, "jti-old")
                await register_session(user, "jti-new")

                self.assertFalse(await is_session_active("user-1", "jti-old"))
                self.assertTrue(await is_session_active("user-1", "jti-new"))


if __name__ == "__main__":
    unittest.main()
