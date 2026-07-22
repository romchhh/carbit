"""Метадані Telethon-сесії без відкриття .session (SQLite lock у worker)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings


def meta_file_path() -> Path:
    return Path(settings.session_path).parent / "telethon_session_meta.json"


def read_session_meta() -> dict[str, Any] | None:
    path = meta_file_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def write_session_meta(
    *,
    user_id: int,
    first_name: str,
    username: str | None,
    source: str = "auth",
) -> None:
    path = meta_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "authorized": True,
        "user": {
            "id": user_id,
            "first_name": first_name or "",
            "username": username,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_session_meta() -> None:
    path = meta_file_path()
    if path.exists():
        path.unlink()
