from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.services.telegram_channels.ingest import ingest_telegram_listing
from app.services.telegram_channels.service_loader import get_parser_channels, get_parser_service

logger = logging.getLogger(__name__)


def _quiet_telethon_logs() -> None:
    for name in ("telethon", "telethon.network", "telethon.client"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _format_channel_stats(stats: dict) -> str:
    return (
        f"повідомлень {stats.get('messages', 0)}, "
        f"груп {stats.get('groups', 0)}, "
        f"dedupe {stats.get('dedupe', 0)}, "
        f"invalid {stats.get('invalid', 0)}, "
        f"valid {stats.get('valid', 0)}"
    )


async def run_telegram_channels_cycle(
    db: AsyncSession,
    settings: dict,
    log: list[str],
    *,
    ignore_dedupe: bool = False,
) -> int:
    """
    Завантажує нові оголошення з Telegram-каналів у БД.
    Лінкування до пошуків і сповіщення — у загальному циклі парсера (як AUTO.RIA/OLX).
    """
    if not app_settings.TELEGRAM_ENABLED:
        log.append("Telegram: вимкнено (TELEGRAM_ENABLED=false)")
        return 0
    if not settings.get("telegram_enabled", True):
        log.append("Telegram: вимкнено в налаштуваннях парсера")
        return 0

    # Завжди чистимо старі TG-лоти (не потребує Telethon).
    try:
        from app.services.telegram_channels.purge import purge_stale_telegram_listings

        purged = await purge_stale_telegram_listings(db)
        if purged:
            log.append(f"Telegram: видалено {purged} оголошень старших за 3 місяці")
            await db.commit()
    except Exception as exc:
        log.append(f"Telegram purge: {exc}")
        logger.exception("Telegram stale purge failed")

    if not app_settings.TELETHON_API_ID or not app_settings.TELETHON_API_HASH:
        log.append("Telegram: немає TELETHON_API_ID / TELETHON_API_HASH")
        return 0

    channels = await get_parser_channels(db)
    if not channels:
        log.append("Telegram: немає каналів — додайте в адмінці /admin/channels")
        return 0

    try:
        from app.services.health import heartbeat_age_seconds

        age = await heartbeat_age_seconds("telegram_worker")
        if age is not None and age <= 60:
            log.append(
                "Telegram: telegram_worker online — інкремент у окремому процесі, "
                "scheduler не дублює Telethon (уникаємо конфлікт session)"
            )
            return 0
    except Exception:
        pass

    limit = int(settings.get("telegram_history_limit", 100))
    dedupe_note = " (тест без dedupe)" if ignore_dedupe else ""
    log.append(f"Telegram: останні {limit} повідомлень на канал{dedupe_note}")

    _quiet_telethon_logs()
    service = get_parser_service(skip_dedupe=ignore_dedupe)
    total = 0

    try:
        await service.start()
    except Exception as exc:
        log.append(f"Telegram: не вдалось підключитись — {exc}")
        logger.exception("Telegram client start failed")
        return 0

    try:
        for channel in channels:
            try:
                listings = await service.parse_channel_history(channel, limit=limit)
                stats = service.last_parse_stats
                for listing in listings:
                    await ingest_telegram_listing(
                        db,
                        listing,
                        notify=False,
                        link_searches=False,
                        parser_service=service,
                    )
                total += len(listings)
                log.append(
                    f"  ✓ {channel}: {len(listings)} оголошень ({_format_channel_stats(stats)})"
                )
            except Exception as exc:
                log.append(f"  ⚠ Telegram {channel}: {exc}")
                logger.exception("Telegram channel parse failed: %s", channel)
    finally:
        await service.stop()

    log.append(f"Telegram: збережено {total} оголошень")
    return total
