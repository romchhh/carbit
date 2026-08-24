from __future__ import annotations

import asyncio
import html
import logging
import time

from app.core.config import monitor_admin_chat_ids
from app.core.redis import get_redis
from app.services.monitoring.collect import collect_system_status, format_status_message
from app.services.monitoring.models import HealthLevel, SystemStatus
from app.services.telegram.client import telegram_client

logger = logging.getLogger(__name__)

_STATE_PREFIX = "monitor:state:"
_ALERT_COOLDOWN_SECONDS = 900
_DAILY_REPORT_KEY = "monitor:daily_report_sent"


async def notify_monitor_admins(text: str) -> None:
    if not telegram_client.enabled:
        logger.warning("Telegram bot token not configured; monitoring alert skipped")
        return
    chat_ids = monitor_admin_chat_ids()
    if not chat_ids:
        logger.warning("MONITOR_ADMIN_IDS not configured; monitoring alert skipped")
        return
    for chat_id in chat_ids:
        try:
            result = await telegram_client.send_message(chat_id, text)
            if not result or not result.get("ok"):
                logger.error("Failed to send monitoring message to %s", chat_id)
        except Exception:
            logger.exception("Monitoring message failed for %s", chat_id)


async def _get_component_state(component_id: str) -> str | None:
    try:
        redis = await get_redis()
        return await redis.get(f"{_STATE_PREFIX}{component_id}")
    except Exception:
        return None


async def _set_component_state(component_id: str, level: HealthLevel) -> None:
    try:
        redis = await get_redis()
        await redis.setex(f"{_STATE_PREFIX}{component_id}", 86400 * 7, level.value)
    except Exception:
        logger.debug("Failed to store monitor state for %s", component_id, exc_info=True)


async def _alert_cooldown_key(key: str) -> bool:
    """Повертає True якщо можна слати alert."""
    try:
        redis = await get_redis()
        full = f"monitor:alert_cd:{key}"
        if await redis.exists(full):
            return False
        await redis.setex(full, _ALERT_COOLDOWN_SECONDS, "1")
        return True
    except Exception:
        return True


async def process_status_alerts(status: SystemStatus) -> None:
    for comp in status.components:
        prev = await _get_component_state(comp.component_id)
        current = comp.level.value
        await _set_component_state(comp.component_id, comp.level)

        if comp.level in {HealthLevel.OK, HealthLevel.UNKNOWN}:
            if prev in {"down", "degraded"}:
                if await _alert_cooldown_key(f"recover:{comp.component_id}"):
                    await notify_monitor_admins(
                        f"✅ <b>Відновлено:</b> {html.escape(comp.label)}\n{html.escape(comp.detail)}"
                    )
            continue

        if prev == current and prev in {"down", "degraded"}:
            continue

        if not await _alert_cooldown_key(f"fail:{comp.component_id}:{current}"):
            continue

        icon = "🔴" if comp.level == HealthLevel.DOWN else "🟡"
        await notify_monitor_admins(
            f"{icon} <b>Алерт моніторингу</b>\n"
            f"<b>{html.escape(comp.label)}</b>\n"
            f"{html.escape(comp.detail)}"
        )


async def run_monitoring_tick() -> SystemStatus:
    status = await collect_system_status()
    await process_status_alerts(status)
    return status


async def send_daily_report() -> None:
    status = await collect_system_status()
    text = format_status_message(status, title="📊 Щоденний звіт Carbit")
    await notify_monitor_admins(text)


async def run_daily_report_if_due() -> None:
    from app.core.config import settings
    from app.core.timezone import now_kyiv

    now = now_kyiv()
    if now.hour != int(settings.MONITOR_DAILY_REPORT_HOUR):
        return
    if now.minute > 10:
        return

    date_key = now.strftime("%Y-%m-%d")
    try:
        redis = await get_redis()
        marker = f"{_DAILY_REPORT_KEY}:{date_key}"
        if await redis.exists(marker):
            return
        await redis.setex(marker, 86400, "1")
    except Exception:
        logger.debug("Daily report dedupe check failed", exc_info=True)

    await send_daily_report()


def schedule_monitoring_tick() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(run_monitoring_tick())
