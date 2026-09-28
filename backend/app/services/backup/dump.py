from __future__ import annotations

import gzip
import logging
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

from sqlalchemy.engine.url import make_url

from app.core.config import ROOT_DIR, settings

logger = logging.getLogger(__name__)


def _sync_database_url() -> str:
    url = (settings.DATABASE_URL or "").strip()
    return (
        url.replace("postgresql+asyncpg", "postgresql")
        .replace("postgresql+psycopg", "postgresql")
        .replace("postgres+asyncpg", "postgresql")
    )


def _sqlite_path_from_url(url: str) -> Path | None:
    prefix = "sqlite+aiosqlite:///"
    if url.startswith(prefix):
        raw = url[len(prefix) :]
        return Path(raw) if raw.startswith("/") else ROOT_DIR / raw
    if url.startswith("sqlite:///"):
        raw = url[len("sqlite:///") :]
        return Path(raw) if raw.startswith("/") else ROOT_DIR / raw
    return None


def dump_primary_database_gz(dest: Path) -> str:
    """Створює gzip-дамп основної БД. Повертає короткий опис джерела."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    sync_url = _sync_database_url()

    if sync_url.startswith("sqlite"):
        db_path = _sqlite_path_from_url(sync_url)
        if not db_path or not db_path.is_file():
            raise FileNotFoundError(f"SQLite database not found: {db_path}")
        _sqlite_to_gz(db_path, dest)
        return f"sqlite:{db_path.name}"

    if not sync_url.startswith("postgresql"):
        raise ValueError(f"Unsupported DATABASE_URL for backup: {sync_url[:40]}…")

    _postgres_to_gz(sync_url, dest)
    parsed = make_url(sync_url)
    return f"postgres:{parsed.database or 'db'}"


def _sqlite_to_gz(db_path: Path, dest: Path) -> None:
    """SQL dump (iterdump) — переносимо між версіями SQLite."""
    conn = sqlite3.connect(str(db_path))
    try:
        with gzip.open(dest, "wt", encoding="utf-8") as gz:
            for line in conn.iterdump():
                gz.write(line)
                gz.write("\n")
    finally:
        conn.close()


def _postgres_to_gz(sync_url: str, dest: Path) -> None:
    parsed = make_url(sync_url)
    if not shutil.which("pg_dump"):
        raise RuntimeError("pg_dump not found (install postgresql-client)")

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = str(parsed.password)

    cmd = [
        "pg_dump",
        "-h",
        parsed.host or "localhost",
        "-p",
        str(parsed.port or 5432),
        "-U",
        parsed.username or "postgres",
        "-d",
        parsed.database or "postgres",
        "--no-owner",
        "--no-acl",
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert proc.stdout is not None
    try:
        with gzip.open(dest, "wb") as gz:
            while True:
                block = proc.stdout.read(1024 * 1024)
                if not block:
                    break
                gz.write(block)
    finally:
        proc.stdout.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"pg_dump failed ({code}): {stderr[:500]}")


def gzip_plain_file(source: Path, dest: Path) -> None:
    with source.open("rb") as src, gzip.open(dest, "wb") as gz:
        shutil.copyfileobj(src, gz, length=1024 * 1024)
