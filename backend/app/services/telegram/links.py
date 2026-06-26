from app.core.config import settings


def bot_username() -> str:
    return (settings.TELEGRAM_BOT_USERNAME or "").lstrip("@")


def bot_base_url() -> str:
    if settings.TELEGRAM_BOT_URL:
        return settings.TELEGRAM_BOT_URL.rstrip("/")
    username = bot_username()
    if not username:
        return ""
    return f"https://t.me/{username}"


def bot_url(start: str | None = None) -> str:
    base = bot_base_url()
    if not base:
        return ""
    if not start:
        return base
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}start={start}"
