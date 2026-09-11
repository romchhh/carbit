from __future__ import annotations

import asyncio
import html
import logging
import time

from app.core.config import monitor_admin_chat_ids
from app.services.telegram.client import telegram_client

logger = logging.getLogger(__name__)

_COOLDOWN_SECONDS = 300
_TIMEOUT_COOLDOWN_SECONDS = 900
_recent: dict[str, float] = {}
_notify_lock = asyncio.Lock()


def _dedupe_key(source: str, error: str) -> str:
    err = (error or "").strip().lower()
    if "таймаут" in err or "timeout" in err:
        return f"{source}:timeout"
    if "404" in err and ("html" in err or "doctype" in err or "httpoison" in err or ":closed" in err):
        return f"{source}:html404"
    if "обірвав" in err or "тимчасово недоступ" in err:
        return f"{source}:transient"
    return f"{source}:{error[:160]}"


def _safe_error_for_admin(error: str) -> str:
    text = (error or "").strip()
    low = text.lower()
    if "<!doctype" in low or "<html" in low:
        return "AUTO.RIA тимчасово недоступний (HTML 404 від шлюзу)."
    return text[:500]


async def _should_notify(key: str, *, cooldown: float | None = None) -> bool:
    window = cooldown if cooldown is not None else _COOLDOWN_SECONDS
    async with _notify_lock:
        now = time.monotonic()
        last = _recent.get(key, 0.0)
        if now - last < window:
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
    chat_ids = monitor_admin_chat_ids()
    if not chat_ids:
        logger.warning("MONITOR_ADMIN_IDS not configured; skipping admin alert")
        return
    if not telegram_client.enabled:
        logger.warning("Telegram bot token not configured; skipping admin alert")
        return

    dedupe_key = _dedupe_key(source, error)
    cooldown = (
        _TIMEOUT_COOLDOWN_SECONDS
        if dedupe_key.endswith(":timeout")
        else _COOLDOWN_SECONDS
    )
    if not await _should_notify(dedupe_key, cooldown=cooldown):
        return

    lines = [
        f"⚠️ <b>Помилка парсингу: {html.escape(source)}</b>",
        "",
        f"<code>{html.escape(_safe_error_for_admin(error))}</code>",
    ]
    if details:
        lines.extend(["", html.escape(details[:800])])
    if url:
        lines.extend(["", f"🔗 {html.escape(url[:500])}"])

    text = "\n".join(lines)

    try:
        for chat_id in chat_ids:
            result = await telegram_client.send_message(chat_id, text)
            if not result or not result.get("ok"):
                logger.error("Failed to send admin parsing alert to Telegram chat %s", chat_id)
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
