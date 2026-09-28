import gzip
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services.backup.dump import dump_primary_database_gz, gzip_plain_file
from app.services.backup.split import split_file


class TestBackupSplit(unittest.TestCase):
    def test_small_file_not_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.bin"
            path.write_bytes(b"x" * 100)
            parts = split_file(path, max_bytes=1000)
            self.assertEqual(parts, [path])

    def test_large_file_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "big.bin"
            path.write_bytes(b"a" * 2500)
            parts = split_file(path, max_bytes=1000)
            self.assertEqual(len(parts), 3)
            merged = b"".join(p.read_bytes() for p in parts)
            self.assertEqual(merged, path.read_bytes())


class TestSqliteBackup(unittest.TestCase):
    def test_sqlite_dump_creates_gzip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            import sqlite3

            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
            conn.execute("INSERT INTO t (v) VALUES ('hello')")
            conn.commit()
            conn.close()

            dest = Path(tmp) / "out.sql.gz"
            with patch("app.services.backup.dump.settings") as mock_settings:
                mock_settings.DATABASE_URL = f"sqlite+aiosqlite:///{db}"
                source = dump_primary_database_gz(dest)
            self.assertIn("sqlite", source)
            self.assertTrue(dest.is_file())
            with gzip.open(dest, "rt", encoding="utf-8") as gz:
                text = gz.read()
            self.assertIn("CREATE TABLE", text)

    def test_gzip_plain_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "kv.db"
            src.write_bytes(b"kv-data")
            dest = Path(tmp) / "kv.db.gz"
            gzip_plain_file(src, dest)
            self.assertTrue(dest.is_file())
            with gzip.open(dest, "rb") as gz:
                self.assertEqual(gz.read(), b"kv-data")


class TestBackupTelegram(unittest.IsolatedAsyncioTestCase):
    async def test_send_calls_document_per_admin(self) -> None:
        from app.services.backup.telegram_delivery import send_backup_files_to_admins

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "carbit_test.sql.gz"
            path.write_bytes(b"z" * 50)
            with (
                patch(
                    "app.services.backup.telegram_delivery.monitor_admin_chat_ids",
                    return_value=["111", "222"],
                ),
                patch(
                    "app.services.backup.telegram_delivery.telegram_client"
                ) as client,
            ):
                client.enabled = True
                client.send_document = AsyncMock(return_value=True)
                errors = await send_backup_files_to_admins(
                    [path],
                    label="test",
                    max_part_bytes=10_000,
                )
            self.assertEqual(errors, [])
            self.assertEqual(client.send_document.await_count, 2)


if __name__ == "__main__":
    unittest.main()
