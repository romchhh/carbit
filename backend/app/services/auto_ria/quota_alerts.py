"""Попередження адмінам про залишок запитів AUTO.RIA (Telegram)."""

from __future__ import annotations

import asyncio
import html
import logging
from typing import Iterable

from app.core.config import settings
from app.core.redis import get_redis
from app.core.timezone import now_kyiv
from app.services.auto_ria.quota_limits import AUTO_RIA_QUOTA_PACKAGE_LABELS, resolve_auto_ria_quota_limits
from app.services.monitoring.alerts import notify_monitor_admins

logger = logging.getLogger(__name__)

_EXHAUSTED_COOLDOWN_SECONDS = 3600
_WARN_MARKER_TTL_SECONDS = 60 * 60 * 24 * 40


def get_auto_ria_quota_limits() -> tuple[int, int, str | None]:
    """Поточні ліміти для обліку (місяць, година, ключ пакета)."""
    return resolve_auto_ria_quota_limits(
        settings.AUTO_RIA_QUOTA_PACKAGE,
        settings.AUTO_RIA_MONTHLY_QUOTA,
        settings.AUTO_RIA_HOURLY_QUOTA,
    )


def _quota_hint_footer(package_key: str | None) -> str:
    if package_key and package_key != "free":
        label = AUTO_RIA_QUOTA_PACKAGE_LABELS.get(package_key, package_key)
        return (
            f"Облік за пакетом <b>{html.escape(label)}</b>. "
            "Змінити — <code>AUTO_RIA_QUOTA_PACKAGE</code> у "
            "<code>backend/app/core/config.py</code> або пресети в "
            "<code>backend/app/services/auto_ria/quota_limits.py</code>."
        )
    return (
        "Облік за безкоштовним пакетом AUTO.RIA (1 000/міс, 30/год). "
        "Для платного — встановіть <code>AUTO_RIA_QUOTA_PACKAGE=100k</code> у config.py."
    )


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


def is_auto_ria_quota_error(status_code: int | None, message: str) -> bool:
    """403/429 від AUTO.RIA через вичерпаний пакет або rate limit."""
    if status_code == 429:
        return True
    if status_code != 403:
        return False
    low = (message or "").lower()
    markers = (
        "закінчились",
        "закінчили",
        "пакет",
        "quota",
        "rate_limit",
        "over_rate",
        "ліміт",
        "limit exceeded",
        "too many",
    )
    return any(marker in low for marker in markers)


def _remaining_percent(used: int, limit: int) -> float:
    if limit <= 0:
        return 100.0
    left = max(limit - used, 0)
    return (left / limit) * 100.0


def _crossed_threshold(used: int, limit: int, threshold: int) -> bool:
    """True, якщо після цього запиту залишок <= threshold%."""
    if limit <= 0:
        return False
    prev_used = max(used - 1, 0)
    prev_left = _remaining_percent(prev_used, limit)
    curr_left = _remaining_percent(used, limit)
    return prev_left > threshold >= curr_left


async def _mark_sent(marker: str) -> bool:
    """Повертає True, якщо маркер ще не був — можна слати alert."""
    try:
        redis = await get_redis()
        full = f"auto_ria:quota_warn:{marker}"
        if await redis.exists(full):
            return False
        await redis.setex(full, _WARN_MARKER_TTL_SECONDS, "1")
        return True
    except Exception:
        return True


async def _exhausted_cooldown_ok() -> bool:
    try:
        redis = await get_redis()
        key = "auto_ria:quota_warn:exhausted"
        if await redis.exists(key):
            return False
        await redis.setex(key, _EXHAUSTED_COOLDOWN_SECONDS, "1")
        return True
    except Exception:
        return True


def _format_limit_block(label: str, used: int, limit: int) -> list[str]:
    left = max(limit - used, 0)
    pct = _remaining_percent(used, limit)
    return [
        f"<b>{html.escape(label)}</b>",
        f"Використано: {used:,} / {limit:,}".replace(",", " "),
        f"Залишилось: {left:,} ({pct:.0f}%)".replace(",", " "),
    ]


async def _notify_threshold(
    *,
    window: str,
    threshold: int,
    used: int,
    limit: int,
    marker: str,
    package_key: str | None,
) -> None:
    if not await _mark_sent(marker):
        return
    lines = [
        f"⚠️ <b>AUTO.RIA: залишилось ≤{threshold}% ({window})</b>",
        "",
        *_format_limit_block(window, used, limit),
        "",
        _quota_hint_footer(package_key),
    ]
    await notify_monitor_admins("\n".join(lines))


async def _check_window_alerts(
    *,
    window_label: str,
    period_marker: str,
    used: int,
    limit: int,
    thresholds: Iterable[int],
    package_key: str | None,
) -> None:
    if limit <= 0:
        return
    for threshold in thresholds:
        if not _crossed_threshold(used, limit, threshold):
            continue
        await _notify_threshold(
            window=window_label,
            threshold=threshold,
            used=used,
            limit=limit,
            marker=f"{period_marker}:left_{threshold}",
            package_key=package_key,
        )


async def check_auto_ria_quota_alerts() -> None:
    """Після запису запиту — попередити адмінів при 20%/10% залишку."""
    from app.services.admin.api_usage import get_auto_ria_quota_usage

    monthly_limit, hourly_limit, package_key = get_auto_ria_quota_limits()
    if monthly_limit <= 0 and hourly_limit <= 0:
        return

    thresholds = _parse_remaining_thresholds(settings.AUTO_RIA_QUOTA_WARN_REMAINING)
    if not thresholds:
        thresholds = (20, 10)

    usage = await get_auto_ria_quota_usage()
    now = now_kyiv()
    month_marker = now.strftime("%Y-%m")
    hour_marker = now.strftime("%Y-%m-%d-%H")

    if monthly_limit > 0:
        await _check_window_alerts(
            window_label="Місячний ліміт",
            period_marker=f"month:{month_marker}",
            used=usage["month_used"],
            limit=monthly_limit,
            thresholds=thresholds,
            package_key=package_key,
        )

    if hourly_limit > 0:
        await _check_window_alerts(
            window_label="Годинний ліміт",
            period_marker=f"hour:{hour_marker}",
            used=usage["hour_used"],
            limit=hourly_limit,
            thresholds=thresholds,
            package_key=package_key,
        )


async def notify_auto_ria_quota_exhausted(error: str) -> None:
    """Коли API повернув 403/429 про вичерпаний пакет."""
    if not await _exhausted_cooldown_ok():
        return

    from app.services.admin.api_usage import get_auto_ria_quota_usage

    monthly_limit, hourly_limit, package_key = get_auto_ria_quota_limits()
    usage = await get_auto_ria_quota_usage()

    lines = [
        "🔴 <b>AUTO.RIA: ліміт запитів вичерпано</b>",
        "",
        f"<code>{html.escape(error[:1200])}</code>",
    ]

    if monthly_limit > 0 or hourly_limit > 0:
        lines.append("")
        if monthly_limit > 0:
            lines.extend(_format_limit_block("Місячний ліміт (облік)", usage["month_used"], monthly_limit))
            lines.append("")
        if hourly_limit > 0:
            lines.extend(_format_limit_block("Годинний ліміт (облік)", usage["hour_used"], hourly_limit))

    lines.extend(
        [
            "",
            _quota_hint_footer(package_key),
            "",
            "Користувачі бачать часткові результати з кешу. Поповніть пакет або зменшіть навантаження.",
        ]
    )
    await notify_monitor_admins("\n".join(lines))


def schedule_auto_ria_quota_check() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(check_auto_ria_quota_alerts())


def schedule_auto_ria_quota_exhausted(error: str) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(notify_auto_ria_quota_exhausted(error))


def normalize_auto_ria_quota_user_message(status_code: int | None, raw: str) -> str | None:
    """Повідомлення для API-клієнта, якщо це вичерпаний пакет."""
    if not is_auto_ria_quota_error(status_code, raw):
        return None
    if status_code == 429:
        return "AUTO.RIA тимчасово обмежує запити. Спробуйте пізніше."
    return "Ліміт запитів AUTO.RIA вичерпано. Спробуйте пізніше або зверніться до підтримки."
