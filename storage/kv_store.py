"""KV client factory: sqlite:// (default) or redis:// for production scale."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from asyncio import to_thread
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class KVPipeline(Protocol):
    def setex(self, key: str, ttl: int, value: str) -> object: ...
    async def execute(self) -> object: ...


class KVClient(Protocol):
    async def setex(self, key: str, ttl: int, value: str) -> None: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> int: ...
    async def ttl(self, key: str) -> int: ...
    async def incr(self, key: str) -> int: ...
    async def mget(self, *keys: str) -> list[str | None]: ...
    def pipeline(self, transaction: bool = False) -> KVPipeline: ...
    async def ping(self) -> bool: ...
    async def hincrby(self, key: str, field: str, amount: int = 1) -> int: ...
    async def hgetall(self, key: str) -> dict[str, str]: ...
    async def expire(self, key: str, ttl: int) -> None: ...
    async def zadd(self, key: str, mapping: dict[str, float]) -> None: ...
    async def zcard(self, key: str) -> int: ...
    async def zrange(self, key: str, start: int, end: int) -> list[str]: ...
    async def zrem(self, key: str, *members: str) -> None: ...


def resolve_sqlite_path(url: str, root_dir: Path) -> Path:
    prefix = "sqlite://"
    if not url.startswith(prefix):
        raise ValueError(f"Unsupported KV URL (use sqlite://): {url}")
    raw_path = url[len(prefix) :].lstrip("/")
    db_path = Path(raw_path) if raw_path.startswith("/") else root_dir / raw_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path.resolve()


class _SQLitePipeline:
    def __init__(self, kv: "SQLiteKV"):
        self._kv = kv
        self._ops: list[tuple[str, str, int, str]] = []

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._ops.append(("setex", key, ttl, value))

    async def execute(self) -> None:
        for _, key, ttl, value in self._ops:
            await self._kv.setex(key, ttl, value)


class SQLiteKV:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL
                )
                """
            )

    def _purge_expired(self, conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM kv WHERE expires_at IS NOT NULL AND expires_at <= ?", (time.time(),))

    def _setex_sync(self, key: str, ttl: int, value: str) -> None:
        expires_at = time.time() + ttl
        with self._connect() as conn:
            self._purge_expired(conn)
            conn.execute(
                "INSERT INTO kv(key, value, expires_at) VALUES (?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value, expires_at=excluded.expires_at",
                (key, value, expires_at),
            )

    def _get_sync(self, key: str) -> str | None:
        with self._connect() as conn:
            self._purge_expired(conn)
            row = conn.execute("SELECT value, expires_at FROM kv WHERE key = ?", (key,)).fetchone()
            if not row:
                return None
            value, expires_at = row
            if expires_at is not None and expires_at <= time.time():
                conn.execute("DELETE FROM kv WHERE key = ?", (key,))
                return None
            return value

    def _delete_sync(self, key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM kv WHERE key = ?", (key,))

    def _exists_sync(self, key: str) -> int:
        return 1 if self._get_sync(key) is not None else 0

    def _ttl_sync(self, key: str) -> int:
        with self._connect() as conn:
            self._purge_expired(conn)
            row = conn.execute("SELECT expires_at FROM kv WHERE key = ?", (key,)).fetchone()
            if not row or row[0] is None:
                return -1
            remaining = int(row[0] - time.time())
            return remaining if remaining > 0 else -2

    def _incr_sync(self, key: str) -> int:
        with self._connect() as conn:
            self._purge_expired(conn)
            row = conn.execute("SELECT value, expires_at FROM kv WHERE key = ?", (key,)).fetchone()
            now = time.time()
            if not row:
                new_value = 1
                conn.execute(
                    "INSERT INTO kv(key, value, expires_at) VALUES (?, ?, NULL)",
                    (key, str(new_value)),
                )
                return new_value

            value, expires_at = row
            if expires_at is not None and expires_at <= now:
                new_value = 1
                conn.execute(
                    "UPDATE kv SET value = ?, expires_at = NULL WHERE key = ?",
                    (str(new_value), key),
                )
                return new_value

            try:
                new_value = int(value) + 1
            except (TypeError, ValueError):
                new_value = 1
            conn.execute("UPDATE kv SET value = ? WHERE key = ?", (str(new_value), key))
            return new_value

    async def setex(self, key: str, ttl: int, value: str) -> None:
        await to_thread(self._setex_sync, key, ttl, value)

    async def get(self, key: str) -> str | None:
        return await to_thread(self._get_sync, key)

    async def delete(self, key: str) -> None:
        await to_thread(self._delete_sync, key)

    async def exists(self, key: str) -> int:
        return await to_thread(self._exists_sync, key)

    async def ttl(self, key: str) -> int:
        return await to_thread(self._ttl_sync, key)

    async def incr(self, key: str) -> int:
        return await to_thread(self._incr_sync, key)

    async def mget(self, *keys: str) -> list[str | None]:
        if not keys:
            return []
        return [await self.get(key) for key in keys]

    def pipeline(self, transaction: bool = False) -> _SQLitePipeline:
        return _SQLitePipeline(self)

    async def ping(self) -> bool:
        try:
            await self.setex("kv:ping", 10, "1")
            return (await self.get("kv:ping")) == "1"
        except Exception:
            return False

    def _load_hash_sync(self, conn: sqlite3.Connection, key: str) -> dict[str, int]:
        row = conn.execute("SELECT value, expires_at FROM kv WHERE key = ?", (key,)).fetchone()
        if not row:
            return {}
        value, expires_at = row
        if expires_at is not None and expires_at <= time.time():
            conn.execute("DELETE FROM kv WHERE key = ?", (key,))
            return {}
        if not value:
            return {}
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if not isinstance(raw, dict):
            return {}
        out: dict[str, int] = {}
        for field, amount in raw.items():
            try:
                out[str(field)] = int(amount)
            except (TypeError, ValueError):
                continue
        return out

    def _save_hash_sync(
        self,
        conn: sqlite3.Connection,
        key: str,
        data: dict[str, int],
        *,
        preserve_expiry: bool = True,
    ) -> None:
        expires_at: float | None = None
        if preserve_expiry:
            row = conn.execute("SELECT expires_at FROM kv WHERE key = ?", (key,)).fetchone()
            if row:
                expires_at = row[0]
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        conn.execute(
            "INSERT INTO kv(key, value, expires_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, payload, expires_at),
        )

    def _hincrby_sync(self, key: str, field: str, amount: int) -> int:
        with self._connect() as conn:
            self._purge_expired(conn)
            data = self._load_hash_sync(conn, key)
            new_value = int(data.get(field, 0)) + int(amount)
            data[field] = new_value
            self._save_hash_sync(conn, key, data)
            return new_value

    def _hgetall_sync(self, key: str) -> dict[str, str]:
        with self._connect() as conn:
            self._purge_expired(conn)
            data = self._load_hash_sync(conn, key)
            return {field: str(value) for field, value in data.items()}

    def _expire_sync(self, key: str, ttl: int) -> None:
        expires_at = time.time() + max(int(ttl), 1)
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM kv WHERE key = ?", (key,)).fetchone()
            if not row:
                return
            conn.execute("UPDATE kv SET expires_at = ? WHERE key = ?", (expires_at, key))

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        return await to_thread(self._hincrby_sync, key, field, amount)

    async def hgetall(self, key: str) -> dict[str, str]:
        return await to_thread(self._hgetall_sync, key)

    async def expire(self, key: str, ttl: int) -> None:
        await to_thread(self._expire_sync, key, ttl)

    def _load_zset_sync(self, conn: sqlite3.Connection, key: str) -> dict[str, float]:
        row = conn.execute("SELECT value, expires_at FROM kv WHERE key = ?", (key,)).fetchone()
        if not row:
            return {}
        value, expires_at = row
        if expires_at is not None and expires_at <= time.time():
            conn.execute("DELETE FROM kv WHERE key = ?", (key,))
            return {}
        if not value:
            return {}
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if not isinstance(raw, dict):
            return {}
        out: dict[str, float] = {}
        for member, score in raw.items():
            try:
                out[str(member)] = float(score)
            except (TypeError, ValueError):
                continue
        return out

    def _save_zset_sync(
        self,
        conn: sqlite3.Connection,
        key: str,
        data: dict[str, float],
        *,
        preserve_expiry: bool = True,
    ) -> None:
        expires_at: float | None = None
        if preserve_expiry:
            row = conn.execute("SELECT expires_at FROM kv WHERE key = ?", (key,)).fetchone()
            if row:
                expires_at = row[0]
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        conn.execute(
            "INSERT INTO kv(key, value, expires_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, payload, expires_at),
        )

    def _zadd_sync(self, key: str, mapping: dict[str, float]) -> None:
        with self._connect() as conn:
            self._purge_expired(conn)
            data = self._load_zset_sync(conn, key)
            for member, score in mapping.items():
                data[str(member)] = float(score)
            self._save_zset_sync(conn, key, data)

    def _zcard_sync(self, key: str) -> int:
        with self._connect() as conn:
            self._purge_expired(conn)
            return len(self._load_zset_sync(conn, key))

    def _zrange_sync(self, key: str, start: int, end: int) -> list[str]:
        with self._connect() as conn:
            self._purge_expired(conn)
            data = self._load_zset_sync(conn, key)
            items = sorted(data.items(), key=lambda item: (item[1], item[0]))
            if end < 0:
                sliced = items[start:]
            else:
                sliced = items[start : end + 1]
            return [member for member, _ in sliced]

    def _zrem_sync(self, key: str, *members: str) -> None:
        with self._connect() as conn:
            self._purge_expired(conn)
            data = self._load_zset_sync(conn, key)
            changed = False
            for member in members:
                if str(member) in data:
                    del data[str(member)]
                    changed = True
            if changed:
                if data:
                    self._save_zset_sync(conn, key, data)
                else:
                    conn.execute("DELETE FROM kv WHERE key = ?", (key,))

    async def zadd(self, key: str, mapping: dict[str, float]) -> None:
        await to_thread(self._zadd_sync, key, mapping)

    async def zcard(self, key: str) -> int:
        return await to_thread(self._zcard_sync, key)

    async def zrange(self, key: str, start: int, end: int) -> list[str]:
        return await to_thread(self._zrange_sync, key, start, end)

    async def zrem(self, key: str, *members: str) -> None:
        await to_thread(self._zrem_sync, key, *members)


class RedisKV:
    """Thin async wrapper around redis.asyncio."""

    def __init__(self, url: str):
        import redis.asyncio as redis

        self._client = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
            retry_on_timeout=False,
        )

    async def setex(self, key: str, ttl: int, value: str) -> None:
        await self._client.setex(key, ttl, value)

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def exists(self, key: str) -> int:
        return int(await self._client.exists(key))

    async def ttl(self, key: str) -> int:
        return int(await self._client.ttl(key))

    async def incr(self, key: str) -> int:
        return int(await self._client.incr(key))

    async def mget(self, *keys: str) -> list[str | None]:
        if not keys:
            return []
        raw = await self._client.mget(*keys)
        return list(raw)

    def pipeline(self, transaction: bool = False) -> KVPipeline:
        return self._client.pipeline(transaction=transaction)

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        return int(await self._client.hincrby(key, field, amount))

    async def hgetall(self, key: str) -> dict[str, str]:
        raw = await self._client.hgetall(key)
        if not raw:
            return {}
        return {str(field): str(value) for field, value in raw.items()}

    async def expire(self, key: str, ttl: int) -> None:
        await self._client.expire(key, max(int(ttl), 1))

    async def zadd(self, key: str, mapping: dict[str, float]) -> None:
        await self._client.zadd(key, mapping)

    async def zcard(self, key: str) -> int:
        return int(await self._client.zcard(key))

    async def zrange(self, key: str, start: int, end: int) -> list[str]:
        raw = await self._client.zrange(key, start, end)
        return [str(item) for item in raw]

    async def zrem(self, key: str, *members: str) -> None:
        if members:
            await self._client.zrem(key, *members)

    async def aclose(self) -> None:
        await self._client.aclose()


_clients: dict[str, KVClient] = {}


def _sqlite_fallback(root_dir: Path) -> SQLiteKV:
    return SQLiteKV(resolve_sqlite_path("sqlite://database/kv.db", root_dir))


def get_kv_client(url: str, root_dir: Path) -> KVClient:
    if url in _clients:
        return _clients[url]

    if url.startswith("redis://") or url.startswith("rediss://"):
        try:
            client: KVClient = RedisKV(url)
        except Exception as exc:
            logger.warning("Redis client init failed (%s) — falling back to SQLite KV", exc)
            client = _sqlite_fallback(root_dir)
            _clients[url] = client
            return client
    elif url.startswith("sqlite://"):
        client = SQLiteKV(resolve_sqlite_path(url, root_dir))
    else:
        raise ValueError(f"Unsupported REDIS_URL scheme: {url}")

    _clients[url] = client
    return client


async def open_kv_client(url: str, root_dir: Path) -> KVClient:
    """Create KV client and verify Redis connectivity; fall back to SQLite if needed."""
    client = get_kv_client(url, root_dir)
    if isinstance(client, RedisKV):
        try:
            ok = await client.ping()
        except Exception as exc:
            logger.warning("Redis ping failed (%s) — falling back to SQLite KV", exc)
            ok = False
        if not ok:
            try:
                await client.aclose()
            except Exception:
                pass
            fallback = _sqlite_fallback(root_dir)
            _clients[url] = fallback
            return fallback
    return client
