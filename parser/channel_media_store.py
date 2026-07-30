"""
Курсори каналів + черга лінивого завантаження фото (SQLite поруч із dedupe).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

from .config import settings

_lock = threading.Lock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChannelMediaStore:
    """Курсор історії каналу + refs/черга фото для lazy download."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS channel_cursors (
                    channel TEXT PRIMARY KEY,
                    last_message_id INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS listing_photo_refs (
                    listing_id TEXT PRIMARY KEY,
                    channel TEXT NOT NULL,
                    message_ids TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS photo_download_queue (
                    listing_id TEXT PRIMARY KEY,
                    enqueued_at TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS keyword_search_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    limit_n INTEGER NOT NULL DEFAULT 40,
                    status TEXT NOT NULL DEFAULT 'pending',
                    found INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    enqueued_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_keyword_search_status
                    ON keyword_search_queue (status, enqueued_at);
                """
            )
            conn.commit()

    def get_cursor(self, channel: str) -> int:
        with _lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT last_message_id FROM channel_cursors WHERE channel=?",
                (channel,),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def advance_cursor(self, channel: str, message_id: int) -> None:
        if message_id <= 0:
            return
        with _lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT last_message_id FROM channel_cursors WHERE channel=?",
                (channel,),
            )
            row = cur.fetchone()
            current = int(row[0]) if row else 0
            nxt = max(current, int(message_id))
            conn.execute(
                """
                INSERT INTO channel_cursors (channel, last_message_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(channel) DO UPDATE SET
                    last_message_id = excluded.last_message_id,
                    updated_at = excluded.updated_at
                """,
                (channel, nxt, _utcnow()),
            )
            conn.commit()

    def save_photo_refs(self, listing_id: str, channel: str, message_ids: list[int]) -> None:
        ids = [int(x) for x in message_ids if x]
        if not ids:
            return
        with _lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO listing_photo_refs (listing_id, channel, message_ids, status, updated_at)
                VALUES (?, ?, ?, 'pending', ?)
                ON CONFLICT(listing_id) DO UPDATE SET
                    channel = excluded.channel,
                    message_ids = excluded.message_ids,
                    status = CASE
                        WHEN listing_photo_refs.status = 'done' THEN 'done'
                        ELSE 'pending'
                    END,
                    updated_at = excluded.updated_at
                """,
                (listing_id, channel, json.dumps(ids), _utcnow()),
            )
            conn.commit()

    def get_photo_refs(self, listing_id: str) -> tuple[str, list[int], str] | None:
        with _lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT channel, message_ids, status FROM listing_photo_refs WHERE listing_id=?",
                (listing_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                ids = [int(x) for x in json.loads(row[1])]
            except (TypeError, ValueError, json.JSONDecodeError):
                ids = []
            return str(row[0]), ids, str(row[2])

    def mark_photos_done(self, listing_id: str) -> None:
        with _lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE listing_photo_refs
                SET status='done', updated_at=?
                WHERE listing_id=?
                """,
                (_utcnow(), listing_id),
            )
            conn.execute(
                "DELETE FROM photo_download_queue WHERE listing_id=?",
                (listing_id,),
            )
            conn.commit()

    def mark_photos_failed(self, listing_id: str) -> None:
        with _lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE listing_photo_refs
                SET status='failed', updated_at=?
                WHERE listing_id=?
                """,
                (_utcnow(), listing_id),
            )
            conn.execute(
                "DELETE FROM photo_download_queue WHERE listing_id=?",
                (listing_id,),
            )
            conn.commit()

    def enqueue_photo_download(self, listing_id: str) -> bool:
        """Повертає True, якщо реально поставили в чергу (ще не done)."""
        refs = self.get_photo_refs(listing_id)
        if not refs:
            return False
        _, _, status = refs
        if status == "done":
            return False
        with _lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO photo_download_queue (listing_id, enqueued_at, attempts)
                VALUES (?, ?, 0)
                ON CONFLICT(listing_id) DO NOTHING
                """,
                (listing_id, _utcnow()),
            )
            conn.commit()
        return True

    def claim_photo_jobs(self, *, limit: int = 5) -> list[str]:
        with _lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT listing_id FROM photo_download_queue
                ORDER BY enqueued_at ASC
                LIMIT ?
                """,
                (limit,),
            )
            ids = [str(row[0]) for row in cur.fetchall()]
            for listing_id in ids:
                conn.execute(
                    """
                    UPDATE photo_download_queue
                    SET attempts = attempts + 1
                    WHERE listing_id=?
                    """,
                    (listing_id,),
                )
            conn.commit()
            return ids

    def enqueue_keyword_searches(
        self,
        query: str,
        channels: list[str],
        *,
        limit: int = 40,
        cooldown_seconds: int = 120,
        skip_cooldown: bool = False,
    ) -> list[int]:
        """Ставить keyword-scan по кожному каналу. Повертає id джобів для очікування."""
        query = (query or "").strip()
        if not query or not channels:
            return []

        limit = max(10, min(int(limit), 2500))
        cooldown_seconds = max(30, int(cooldown_seconds))
        job_ids: list[int] = []
        now = _utcnow()

        with _lock, sqlite3.connect(self.db_path) as conn:
            for channel in channels:
                ch = (channel or "").strip()
                if not ch:
                    continue
                # Активний той самий запит — чекаємо його
                cur = conn.execute(
                    """
                    SELECT id FROM keyword_search_queue
                    WHERE query=? AND channel=? AND status IN ('pending', 'running')
                    ORDER BY id DESC LIMIT 1
                    """,
                    (query, ch),
                )
                row = cur.fetchone()
                if row:
                    job_ids.append(int(row[0]))
                    continue

                # Свіжий done — не ганяємо Telethon знову
                cur = conn.execute(
                    """
                    SELECT id, finished_at FROM keyword_search_queue
                    WHERE query=? AND channel=? AND status='done'
                    ORDER BY id DESC LIMIT 1
                    """,
                    (query, ch),
                )
                done = cur.fetchone()
                if done and done[1] and not skip_cooldown:
                    try:
                        finished = datetime.fromisoformat(str(done[1]))
                        if finished.tzinfo is None:
                            finished = finished.replace(tzinfo=timezone.utc)
                        age = (datetime.now(timezone.utc) - finished).total_seconds()
                        if age < cooldown_seconds:
                            job_ids.append(int(done[0]))
                            continue
                    except ValueError:
                        pass

                cur = conn.execute(
                    """
                    INSERT INTO keyword_search_queue
                        (query, channel, limit_n, status, found, enqueued_at)
                    VALUES (?, ?, ?, 'pending', 0, ?)
                    """,
                    (query, ch, limit, now),
                )
                job_ids.append(int(cur.lastrowid))
            conn.commit()
        return job_ids

    def cancel_stale_keyword_jobs(self, *, older_than_seconds: int = 1800) -> int:
        """Скидає застарілі pending/running джоби, щоб live-пошук не чекав годинами."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max(60, int(older_than_seconds)))
        with _lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                UPDATE keyword_search_queue
                SET status='error', error=?, finished_at=?
                WHERE status IN ('pending', 'running')
                  AND enqueued_at < ?
                """,
                ("stale/cancelled", _utcnow(), cutoff.isoformat()),
            )
            conn.commit()
            return int(cur.rowcount or 0)

    def claim_keyword_jobs(self, *, limit: int = 4) -> list[dict]:
        with _lock, sqlite3.connect(self.db_path) as conn:
            # Telethon search (plain query) — швидко знаходить старі пости;
            # __scan__ повзунок історії — повільний і має йти після.
            cur = conn.execute(
                """
                SELECT id, query, channel, limit_n FROM keyword_search_queue
                WHERE status='pending'
                ORDER BY
                  CASE WHEN query LIKE '__scan__:%' THEN 1 ELSE 0 END ASC,
                  enqueued_at ASC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
            jobs: list[dict] = []
            for row in rows:
                job_id = int(row[0])
                conn.execute(
                    "UPDATE keyword_search_queue SET status='running' WHERE id=?",
                    (job_id,),
                )
                jobs.append(
                    {
                        "id": job_id,
                        "query": str(row[1]),
                        "channel": str(row[2]),
                        "limit": int(row[3] or 40),
                    }
                )
            conn.commit()
            return jobs

    def finish_keyword_job(
        self,
        job_id: int,
        *,
        found: int = 0,
        error: str | None = None,
    ) -> None:
        with _lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE keyword_search_queue
                SET status=?, found=?, error=?, finished_at=?
                WHERE id=?
                """,
                (
                    "error" if error else "done",
                    int(found or 0),
                    (error or None),
                    _utcnow(),
                    int(job_id),
                ),
            )
            conn.commit()

    def keyword_jobs_pending(self, job_ids: list[int]) -> bool:
        if not job_ids:
            return False
        with _lock, sqlite3.connect(self.db_path) as conn:
            placeholders = ",".join("?" for _ in job_ids)
            cur = conn.execute(
                f"""
                SELECT 1 FROM keyword_search_queue
                WHERE id IN ({placeholders}) AND status IN ('pending', 'running')
                LIMIT 1
                """,
                [int(x) for x in job_ids],
            )
            return cur.fetchone() is not None

    def reset_stuck_running_jobs(self, *, older_than_seconds: int = 300) -> int:
        """Переводить 'running' → 'error' якщо воркер впав і не завершив job."""
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)).isoformat()
        with _lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                UPDATE keyword_search_queue
                SET status='error', error='Stuck running — worker crash', finished_at=?
                WHERE status='running' AND enqueued_at < ?
                """,
                (_utcnow(), cutoff),
            )
            conn.commit()
            return cur.rowcount

    def keyword_queue_stats(self) -> dict[str, int]:
        with _lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) FROM keyword_search_queue
                GROUP BY status
                """
            ).fetchall()
        out = {"pending": 0, "running": 0, "done": 0, "error": 0}
        for status, count in rows:
            key = str(status or "").lower()
            if key in out:
                out[key] = int(count)
        return out
