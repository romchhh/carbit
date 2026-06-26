"""Локальне key-value сховище (Redis-подібний API) на SQLite."""
from __future__ import annotations

import sqlite3
import time
from asyncio import to_thread
from pathlib import Path
from typing import Protocol


class KVClient(Protocol):
    async def setex(self, key: str, ttl: int, value: str) -> None: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> int: ...
    async def ttl(self, key: str) -> int: ...


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
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
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


_clients: dict[str, KVClient] = {}


def get_kv_client(url: str, root_dir: Path) -> KVClient:
    if url in _clients:
        return _clients[url]

    db_path = resolve_sqlite_path(url, root_dir)
    client: KVClient = SQLiteKV(db_path)
    _clients[url] = client
    return client
