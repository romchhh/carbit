from __future__ import annotations

from pathlib import Path

from app.core.config import settings

TELEGRAM_MEDIA_API_PREFIX = "/api/v1/telegram-media/"


def public_site_base() -> str:
    base = (settings.PUBLIC_API_BASE or "").rstrip("/")
    if base.endswith("/api/v1"):
        return base[: -len("/api/v1")]
    return settings.FRONTEND_URL.rstrip("/")


def resolve_listing_image_url(url: str | None) -> str | None:
    if not url:
        return None
    normalized = str(url).strip()
    if not normalized:
        return None
    if normalized.startswith(("http://", "https://")):
        return normalized
    if normalized.startswith("/"):
        return f"{public_site_base()}{normalized}"
    return normalized


def telegram_media_local_path(api_path: str | None) -> Path | None:
    if not api_path or not str(api_path).startswith(TELEGRAM_MEDIA_API_PREFIX):
        return None
    rel = str(api_path).removeprefix(TELEGRAM_MEDIA_API_PREFIX)
    path = Path(settings.TELEGRAM_MEDIA_DIR) / rel
    return path if path.is_file() and path.stat().st_size > 0 else None


def filter_existing_image_urls(urls: list[str] | None) -> list[str]:
    """Залишає remote URL; telegram-media — лише якщо файл ще є на диску."""
    out: list[str] = []
    for raw in urls or []:
        if not isinstance(raw, str):
            continue
        value = raw.strip()
        if not value:
            continue
        if value.startswith(TELEGRAM_MEDIA_API_PREFIX):
            if telegram_media_local_path(value) is not None:
                out.append(value)
            continue
        if value.startswith(("http://", "https://")):
            out.append(value)
    return out


def is_public_http_url(url: str) -> bool:
    lowered = url.lower()
    if lowered.startswith("https://"):
        return True
    if lowered.startswith("http://") and "localhost" not in lowered and "127.0.0.1" not in lowered:
        return True
    return False
