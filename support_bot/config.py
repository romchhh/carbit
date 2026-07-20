from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        extra="ignore",
    )

    TELEGRAM_SUPPORT_BOT_TOKEN: str = ""
    # Куди форвардити звернення (chat_id адміна / групи)
    TELEGRAM_SUPPORT_ADMIN_CHAT_ID: str = ""
    # Fallback на загальний admin chat
    TELEGRAM_ADMIN_CHAT_ID: str = "585621771"
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def admin_chat_id(self) -> str:
        return (self.TELEGRAM_SUPPORT_ADMIN_CHAT_ID or self.TELEGRAM_ADMIN_CHAT_ID or "").strip()


settings = Settings()
