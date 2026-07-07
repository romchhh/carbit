from __future__ import annotations

import asyncio
import html
import logging
import time

from app.core.config import settings
from app.services.telegram.client import telegram_client

logger = logging.getLogger(__name__)

_COOLDOWN_SECONDS = 300
_recent: dict[str, float] = {}


def _should_notify(key: str) -> bool:
    now = time.monotonic()
    last = _recent.get(key, 0.0)
    if now - last < _COOLDOWN_SECONDS:
        return False
    _recent[key] = now
    return True


async def notify_admin_parsing_error(
    *,
    source: str,
    error: str,
    details: str | None = None,
    url: str | None = None,
) -> None:
    """Надсилає адміну повідомлення про проблему парсингу (з cooldown, щоб не спамити)."""
    chat_id = (settings.TELEGRAM_ADMIN_CHAT_ID or "").strip()
    if not chat_id:
        logger.warning("TELEGRAM_ADMIN_CHAT_ID not configured; skipping admin alert")
        return
    if not telegram_client.enabled:
        logger.warning("Telegram bot token not configured; skipping admin alert")
        return

    dedupe_key = f"{source}:{error[:160]}"
    if not _should_notify(dedupe_key):
        return

    lines = [
        f"⚠️ <b>Помилка парсингу: {html.escape(source)}</b>",
        "",
        f"<code>{html.escape(error[:1800])}</code>",
    ]
    if details:
        lines.extend(["", html.escape(details[:800])])
    if url:
        lines.extend(["", f"🔗 {html.escape(url[:500])}"])

    text = "\n".join(lines)

    try:
        result = await telegram_client.send_message(chat_id, text)
        if not result or not result.get("ok"):
            logger.error("Failed to send admin parsing alert to Telegram")
    except Exception:
        logger.exception("Exception while sending admin parsing alert")


def schedule_admin_parsing_error(
    *,
    source: str,
    error: str,
    details: str | None = None,
    url: str | None = None,
) -> None:
    """Fire-and-forget wrapper for sync contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("No running event loop; admin alert skipped: %s", error)
        return
    loop.create_task(
        notify_admin_parsing_error(source=source, error=error, details=details, url=url)
    )
