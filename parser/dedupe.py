"""
Проста SQLite-дедуплікація: щоб при повторному запуску / реальному часі
не парсити одне й те саме оголошення двічі.
"""
import sqlite3
import threading

from .config import settings

_lock = threading.Lock()


class DedupeStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_messages (
                    channel TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    PRIMARY KEY (channel, message_id)
                )
                """
            )
            conn.commit()

    def is_seen(self, channel: str, message_id: int) -> bool:
        with _lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT 1 FROM seen_messages WHERE channel=? AND message_id=?",
                (channel, message_id),
            )
            return cur.fetchone() is not None

    def mark_seen(self, channel: str, message_ids: list):
        with _lock, sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO seen_messages (channel, message_id) VALUES (?, ?)",
                [(channel, mid) for mid in message_ids],
            )
            conn.commit()

    def clear(self):
        with _lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM seen_messages")
            conn.commit()