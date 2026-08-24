from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        extra="ignore",
    )

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_BOT_URL: str = ""
    REDIS_URL: str = "sqlite://database/kv.db"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000/api/v1"
    INTERNAL_API_SECRET: str = "change-me-internal"
    MONITOR_ADMIN_IDS: str = "1734355788,7119952932"

    def monitor_admin_ids(self) -> set[str]:
        raw = (self.MONITOR_ADMIN_IDS or "").replace(";", ",")
        return {part.strip() for part in raw.split(",") if part.strip()}


settings = Settings()
