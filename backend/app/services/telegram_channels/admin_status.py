"""Статус Telegram worker і черги для адмінки."""

from __future__ import annotations

from app.core.config import settings as app_settings
from app.services.health import heartbeat_age_seconds
from app.services.parser.settings import get_parser_settings
from app.services.telegram_channels.bootstrap import ensure_parser_path


async def get_telegram_worker_status() -> dict:
    settings = await get_parser_settings()
    age = await heartbeat_age_seconds("telegram_worker")
    online = age is not None and age <= 45

    keyword_queue = {"pending": 0, "running": 0, "done": 0, "error": 0}
    try:
        ensure_parser_path()
        from parser.channel_media_store import ChannelMediaStore

        keyword_queue = ChannelMediaStore().keyword_queue_stats()
    except Exception:
        pass

    poll = int(settings.get("telegram_worker_poll_seconds") or 3)
    sync = int(settings.get("telegram_channel_sync_seconds") or 45)
    scheduler = int(settings.get("interval_seconds") or 900)

    return {
        "telegram_enabled": bool(app_settings.TELEGRAM_ENABLED and settings.get("telegram_enabled", True)),
        "telethon_configured": bool(app_settings.TELETHON_API_ID and app_settings.TELETHON_API_HASH),
        "worker_online": online,
        "worker_heartbeat_age_seconds": round(age, 1) if age is not None else None,
        "interval_seconds": scheduler,
        "telegram_worker_poll_seconds": poll,
        "telegram_channel_sync_seconds": sync,
        "telegram_history_limit": int(settings.get("telegram_history_limit") or 500),
        "keyword_queue": keyword_queue,
        "schedule_hint": (
            f"Плановий збір (worker): кожні {scheduler} с · "
            f"telegram_worker: keyword/фото кожні {poll} с · "
            f"sync каналів кожні {sync} с · realtime — нові пости одразу"
        ),
    }
