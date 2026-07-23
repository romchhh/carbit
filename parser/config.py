"""
Конфігурація парсера Telegram-каналів (.env у корені проєкту).

Список каналів більше не з env — керується в адмінці (таблиця telegram_channels).
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    api_id: int = int(os.getenv("TELETHON_API_ID") or os.getenv("TG_API_ID") or "0")
    api_hash: str = os.getenv("TELETHON_API_HASH") or os.getenv("TG_API_HASH") or ""
    session_name: str = (
        (os.getenv("TELETHON_SESSION_NAME") or os.getenv("TG_SESSION_NAME") or "carbit_parser")
        .strip()
        or "carbit_parser"
    )
    phone: str = os.getenv("TELETHON_NUMBER") or os.getenv("TG_PHONE") or os.getenv("TELEGRAM_PHONE") or ""

    @property
    def session_path(self) -> str:
        custom = os.getenv("TELETHON_SESSION_PATH", "").strip()
        if custom:
            return custom
        return str(ROOT / "database" / self.session_name)

    @property
    def session_file(self) -> str:
        return f"{self.session_path}.session"

    media_dir: str = os.getenv(
        "TELEGRAM_MEDIA_DIR",
        os.getenv("MEDIA_DIR", str(ROOT / "media")),
    )

    db_path: str = os.getenv(
        "TELEGRAM_DEDUPE_DB",
        os.getenv("DB_PATH", str(ROOT / "database" / "telegram_parser.db")),
    )

    webhook_url: str = os.getenv("WEBHOOK_URL", "")
    max_photos_per_listing: int = int(os.getenv("TELEGRAM_MAX_PHOTOS", "3"))


settings = Settings()
