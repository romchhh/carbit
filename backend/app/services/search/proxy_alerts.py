"""Telegram-алерти: Webshare проксі зламався або кінчається трафік/підписка."""

from __future__ import annotations

import html
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.core.redis import get_redis
from app.services.monitoring.alerts import notify_monitor_admins
from app.services.search.http_proxy import (
    WebshareUsage,
    fetch_webshare_usage,
    format_bytes_gb,
    humanize_proxy_error,
    proxy_configured,
)

logger = logging.getLogger(__name__)

_WARN_TTL_SECONDS = 60 * 60 * 24 * 40
_FAIL_COOLDOWN_SECONDS = 900
_SUB_SOON_DAYS = 3


def _parse_remaining_thresholds(raw: str) -> tuple[int, ...]:
    out: list[int] = []
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            continue
        if 0 < value < 100:
            out.append(value)
    return tuple(sorted(set(out), reverse=True))


async def _mark_once(key: str, ttl: int) -> bool:
    try:
        redis = await get_redis()
        full = f"webshare:alert:{key}"
        if await redis.exists(full):
            return False
        await redis.setex(full, ttl, "1")
        return True
    except Exception:
        return True


def _period_key(usage: WebshareUsage) -> str:
    return (usage.period_end or "cycle")[:10]


def _parse_end(value: str | None) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


async def notify_proxy_problem(*, source: str, error: str) -> None:
    """Проблема на запиті (407, тунель, ліміт). Cooldown 15 хв."""
    if not await _mark_once(f"fail:{source}", _FAIL_COOLDOWN_SECONDS):
        return
    detail = humanize_proxy_error(error or "")
    await notify_monitor_admins(
        "⚠️ <b>Проксі Webshare</b>\n"
        f"Джерело: <b>{html.escape(source)}</b>\n"
        f"{html.escape(detail)}"
    )


def schedule_proxy_problem(*, source: str, error: str) -> None:
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(notify_proxy_problem(source=source, error=error))


async def check_webshare_alerts() -> None:
    """Викликається з моніторинг-циклу: трафік, дата підписки, доступність API."""
    if not proxy_configured():
        return
    usage = await fetch_webshare_usage()
    if usage is None:
        if await _mark_once("usage_unreadable", _FAIL_COOLDOWN_SECONDS):
            await notify_monitor_admins(
                "⚠️ <b>Проксі Webshare</b>\n"
                "Не вдалося зчитати ліміт трафіку. Перевірте API-ключ у "
                "<a href=\"https://dashboard.webshare.io/\">кабінеті</a>."
            )
        return

    period = _period_key(usage)
    thresholds = _parse_remaining_thresholds(settings.WEBSHARE_BANDWIDTH_WARN_REMAINING)
    if usage.limit_bytes > 0 and usage.remaining_bytes <= 0:
        if await _mark_once(f"exhausted:{period}", _WARN_TTL_SECONDS):
            await notify_monitor_admins(
                "🔴 <b>Проксі Webshare: трафік вичерпано</b>\n"
                f"Використано {format_bytes_gb(usage.used_bytes)} з "
                f"{usage.limit_gb:g} ГБ. Пошук OLX/AUTO.RIA HTML зупиниться, "
                "доки не оновиться цикл або тариф."
            )
        return

    for threshold in thresholds:
        if usage.remaining_pct <= threshold:
            if await _mark_once(f"bw:{period}:{threshold}", _WARN_TTL_SECONDS):
                await notify_monitor_admins(
                    "🟡 <b>Проксі Webshare: закінчується трафік</b>\n"
                    f"Лишилось <b>{usage.remaining_pct:.0f}%</b> "
                    f"({format_bytes_gb(usage.remaining_bytes)} з {usage.limit_gb:g} ГБ).\n"
                    f"Використано {format_bytes_gb(usage.used_bytes)}."
                )
            break

    end = _parse_end(usage.period_end)
    if end is not None:
        now = datetime.now(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        days = (end - now).days
        if 0 <= days <= _SUB_SOON_DAYS:
            if await _mark_once(f"sub:{period}", _WARN_TTL_SECONDS):
                await notify_monitor_admins(
                    "🟡 <b>Проксі Webshare: підписка закінчується</b>\n"
                    f"До {html.escape(usage.period_end or '')} "
                    f"(~{days} дн.). Поновіть тариф у кабінеті."
                )
