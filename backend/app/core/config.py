import os
from pathlib import Path

from pydantic import field_validator, model_validator
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
    APP_NAME: str = "Carbit API"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

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
    TELEGRAM_ADMIN_CHAT_ID: str = "585621771"

    # OpenAI (голосовий пошук)
    OPENAI_API_KEY: str = ""

    # TurboSMS (підтвердження телефону)
    TURBOSMS_TOKEN: str = ""
    TURBOSMS_SENDER: str = "Carbit"

    # External APIs (reserved for future scrapers)
    AUTO_RIA_API_KEY: str = ""
    IMPERIYA_API_KEY: str = ""
    OLX_CLIENT_ID: str = ""
    OLX_CLIENT_SECRET: str = ""

    # База ДАІ (baza-gai.com.ua) — VIN / номери
    BAZA_GAI_API_KEY: str = ""
    BAZA_GAI_BASE_URL: str = "https://baza-gai.com.ua"

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "https://carbit.info",
        "https://www.carbit.info",
        "https://carbit.telebots.site",
    ]

    # Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "Carbit <info@13vplus.com>"
    FRONTEND_URL: str = "http://localhost:3000"
    PUBLIC_API_BASE: str = ""

    # LiqPay (sandbox_: тестові ключі; бойові — після активації компанії)
    LIQPAY_PUBLIC_KEY: str = ""
    LIQPAY_PRIVATE_KEY: str = ""

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # Internal service-to-service auth (bot → backend)
    INTERNAL_API_SECRET: str = "change-me-internal"

    # Telegram channel parser (Telethon user client)
    TELETHON_API_ID: int = 0
    TELETHON_API_HASH: str = ""
    TELETHON_NUMBER: str = ""
    TELETHON_SESSION_NAME: str = "carbit_parser"
    TELEGRAM_MEDIA_DIR: str = "media"
    TELEGRAM_ENABLED: bool = True
    TELEGRAM_MAX_PHOTOS: int = 1
    TELEGRAM_MEDIA_MAX_WIDTH: int = 1280
    TELEGRAM_MEDIA_JPEG_QUALITY: int = 82

    # Observability
    SENTRY_DSN: str = ""

    @field_validator("LIQPAY_PUBLIC_KEY", "LIQPAY_PRIVATE_KEY", mode="before")
    @classmethod
    def strip_liqpay_keys(cls, value: object) -> str:
        if value is None:
            return ""
        text = str(value).strip().strip('"').strip("'")
        return text

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        if not self.TURBOSMS_TOKEN:
            legacy = os.getenv("turbo_sms_token", "").strip()
            if legacy:
                self.TURBOSMS_TOKEN = legacy
        self.DATABASE_URL = resolve_database_url(self.DATABASE_URL)
        media_path = Path(self.TELEGRAM_MEDIA_DIR)
        if not media_path.is_absolute():
            media_path = ROOT_DIR / media_path
        media_path.mkdir(parents=True, exist_ok=True)
        self.TELEGRAM_MEDIA_DIR = str(media_path.resolve())
        if not self.PUBLIC_API_BASE:
            # Не використовуємо внутрішній Docker URL (http://backend:...) для LiqPay callback.
            backend = os.getenv("BACKEND_URL", "").strip().rstrip("/")
            if backend and "://" in backend and "backend:" not in backend and "localhost" not in backend:
                self.PUBLIC_API_BASE = backend
            else:
                self.PUBLIC_API_BASE = f"{self.FRONTEND_URL.rstrip('/')}/api/v1"
        return self


settings = Settings()
