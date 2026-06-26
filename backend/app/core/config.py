from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"
DEFAULT_SQLITE_PATH = ROOT_DIR / "database" / "autoradar.db"


def resolve_database_url(url: str) -> str:
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith("sqlite"):
        return url

    if url.startswith(prefix):
        raw_path = url[len(prefix) :]
        db_path = Path(raw_path) if raw_path.startswith("/") else ROOT_DIR / raw_path
    else:
        db_path = DEFAULT_SQLITE_PATH

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path.resolve()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        extra="ignore",
    )

    # App
    APP_NAME: str = "AutoRadar API"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database (локально: SQLite у database/autoradar.db)
    DATABASE_URL: str = "sqlite+aiosqlite:///database/autoradar.db"

    # KV store (локально: SQLite у database/kv.db, без окремого Redis)
    REDIS_URL: str = "sqlite://database/kv.db"

    # OAuth / Telegram
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_BOT_URL: str = ""

    # External APIs (reserved for future scrapers)
    AUTO_RIA_API_KEY: str = ""
    OLX_CLIENT_ID: str = ""
    OLX_CLIENT_SECRET: str = ""

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "https://autoradar.ua"]

    # Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "AutoRadar <info@13vplus.com>"
    FRONTEND_URL: str = "http://localhost:3000"

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # Internal service-to-service auth (bot → backend)
    INTERNAL_API_SECRET: str = "change-me-internal"

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        self.DATABASE_URL = resolve_database_url(self.DATABASE_URL)
        return self


settings = Settings()
