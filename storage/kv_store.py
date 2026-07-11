"""KV client factory: sqlite:// (default) or redis:// for production scale."""

from __future__ import annotations

import logging
import sqlite3
import time
from asyncio import to_thread
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class KVClient(Protocol):
    async def setex(self, key: str, ttl: int, value: str) -> None: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> int: ...
    async def ttl(self, key: str) -> int: ...
    async def ping(self) -> bool: ...


def resolve_sqlite_path(url: str, root_dir: Path) -> Path:
    prefix = "sqlite://"
    if not url.startswith(prefix):
        raise ValueError(f"Unsupported KV URL (use sqlite://): {url}")
    raw_path = url[len(prefix) :].lstrip("/")
    db_path = Path(raw_path) if raw_path.startswith("/") else root_dir / raw_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path.resolve()


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

    async def ping(self) -> bool:
        try:
            await self.setex("kv:ping", 10, "1")
            return (await self.get("kv:ping")) == "1"
        except Exception:
            return False


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

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

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
