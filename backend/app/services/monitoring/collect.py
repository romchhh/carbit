from __future__ import annotations

import logging
import time

import httpx
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.timezone import format_kyiv, now_kyiv
from app.models.models import Listing, ParseRun
from app.services.health import (
    TELEGRAM_WORKER_HEARTBEAT_MAX_AGE,
    WORKER_HEARTBEAT_MAX_AGE,
    beat,
    check_database_fast,
    check_kv_fast,
    heartbeat_age_seconds,
    is_heartbeat_online,
)
from app.services.monitoring.catalog import (
    INFRA_COMPONENTS,
    PARSER_LABELS,
    WEB_PARSER_SOURCES,
)
from app.services.monitoring.models import ComponentStatus, HealthLevel, SystemStatus
from app.services.monitoring.parser_status import get_parser_status, is_benign_parser_error

logger = logging.getLogger(__name__)

PARSER_STALE_SECONDS = 6 * 3600


def _frontend_check_url() -> str:
    internal = (settings.FRONTEND_INTERNAL_URL or "").strip().rstrip("/")
    if internal:
        return internal
    return settings.FRONTEND_URL.rstrip("/")


async def _check_frontend() -> ComponentStatus:
    url = _frontend_check_url()
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            res = await client.get(url)
        if res.status_code < 500:
            return ComponentStatus(
                "frontend",
                "Frontend",
                HealthLevel.OK,
                f"HTTP {res.status_code}",
            )
        return ComponentStatus(
            "frontend",
            "Frontend",
            HealthLevel.DOWN,
            f"HTTP {res.status_code}",
        )
    except Exception as exc:
        return ComponentStatus(
            "frontend",
            "Frontend",
            HealthLevel.DOWN,
            f"недоступний ({exc.__class__.__name__})",
        )


async def _check_backend() -> ComponentStatus:
    db_ok = await check_database_fast()
    kv_ok = await check_kv_fast()
    if db_ok and kv_ok:
        return ComponentStatus("backend", "Backend API", HealthLevel.OK, "PostgreSQL + KV OK")
    parts = []
    if not db_ok:
        parts.append("PostgreSQL")
    if not kv_ok:
        parts.append("KV")
    return ComponentStatus(
        "backend",
        "Backend API",
        HealthLevel.DOWN,
        f"проблема: {', '.join(parts)}",
    )


async def _check_heartbeat_service(
    service_id: str,
    label: str,
    *,
    max_age: float,
) -> ComponentStatus:
    age = await heartbeat_age_seconds(service_id)
    if is_heartbeat_online(age, max_age=max_age):
        detail = f"heartbeat {int(age or 0)} с тому"
        return ComponentStatus(service_id, label, HealthLevel.OK, detail, age_seconds=age)
    if age is None:
        return ComponentStatus(service_id, label, HealthLevel.DOWN, "немає heartbeat")
    return ComponentStatus(
        service_id,
        label,
        HealthLevel.DOWN,
        f"offline ({int(age)} с тому)",
        age_seconds=age,
    )


async def _check_worker_fallback() -> ComponentStatus:
    base = await _check_heartbeat_service("worker", "Worker (парсер)", max_age=WORKER_HEARTBEAT_MAX_AGE)
    if base.level == HealthLevel.OK:
        return base

    try:
        async with AsyncSessionLocal() as db:
            last = await db.scalar(select(ParseRun).order_by(ParseRun.started_at.desc()).limit(1))
        if last and last.started_at:
            age = (now_kyiv() - last.started_at).total_seconds()
            if age < WORKER_HEARTBEAT_MAX_AGE:
                return ComponentStatus(
                    "worker",
                    "Worker (парсер)",
                    HealthLevel.OK,
                    f"останній цикл {int(age)} с тому",
                    age_seconds=age,
                )
            return ComponentStatus(
                "worker",
                "Worker (парсер)",
                HealthLevel.DEGRADED,
                f"давно не парсив ({int(age // 3600)} год тому)",
                age_seconds=age,
            )
    except Exception:
        logger.debug("Worker fallback check failed", exc_info=True)
    return base


async def _check_parser(source: str) -> ComponentStatus:
    label = PARSER_LABELS.get(source, source)
    status = await get_parser_status(source)
    now = time.time()

    if status:
        age = max(0.0, now - float(status.get("at") or 0))
        if status.get("ok"):
            if age > PARSER_STALE_SECONDS:
                return ComponentStatus(
                    f"parser:{source}",
                    label,
                    HealthLevel.DEGRADED,
                    f"давно не оновлювався ({int(age // 3600)} год)",
                    age_seconds=age,
                )
            count = int(status.get("count") or 0)
            return ComponentStatus(
                f"parser:{source}",
                label,
                HealthLevel.OK,
                f"OK · {count} огол. · {int(age // 60)} хв тому",
                age_seconds=age,
            )
        err = (status.get("error") or "помилка")[:120]
        count = int(status.get("count") or 0)
        if is_benign_parser_error(err):
            return ComponentStatus(
                f"parser:{source}",
                label,
                HealthLevel.OK,
                f"OK · {count} огол. · {int(age // 60)} хв тому",
                age_seconds=age,
            )
        return ComponentStatus(
            f"parser:{source}",
            label,
            HealthLevel.DEGRADED,
            err,
            age_seconds=age,
        )

    # Fallback: listings in DB (сьогодні)
    try:
        async with AsyncSessionLocal() as db:
            since = now_kyiv().replace(hour=0, minute=0, second=0, microsecond=0)
            count = await db.scalar(
                select(func.count())
                .select_from(Listing)
                .where(Listing.id.like(f"{source}_%"), Listing.found_at >= since)
            )
        if (count or 0) > 0:
            return ComponentStatus(
                f"parser:{source}",
                label,
                HealthLevel.OK,
                f"сьогодні {count} огол. (без heartbeat)",
            )
    except Exception:
        logger.debug("Parser DB fallback failed for %s", source, exc_info=True)

    return ComponentStatus(
        f"parser:{source}",
        label,
        HealthLevel.UNKNOWN,
        "немає даних про останній запуск",
    )


async def _check_telegram_parser() -> ComponentStatus:
    worker = await _check_heartbeat_service(
        "telegram_worker",
        "Telegram worker",
        max_age=TELEGRAM_WORKER_HEARTBEAT_MAX_AGE,
    )
    parser = await _check_parser("telegram")
    if worker.level == HealthLevel.OK and parser.level in {HealthLevel.OK, HealthLevel.UNKNOWN}:
        detail = worker.detail
        if parser.detail and parser.level == HealthLevel.OK:
            detail = f"{worker.detail}; {parser.detail}"
        return ComponentStatus("telegram_parser", "Telegram парсер", HealthLevel.OK, detail, worker.age_seconds)
    if worker.level == HealthLevel.DOWN:
        return ComponentStatus(
            "telegram_parser",
            "Telegram парсер",
            HealthLevel.DOWN,
            worker.detail,
            worker.age_seconds,
        )
    return ComponentStatus(
        "telegram_parser",
        "Telegram парсер",
        parser.level if parser.level != HealthLevel.UNKNOWN else HealthLevel.DEGRADED,
        parser.detail or worker.detail,
        parser.age_seconds or worker.age_seconds,
    )


async def collect_system_status(*, touch_backend_heartbeat: bool = False) -> SystemStatus:
    if touch_backend_heartbeat:
        try:
            await beat("backend")
        except Exception:
            logger.debug("backend self-heartbeat failed", exc_info=True)

    components: list[ComponentStatus] = [
        await _check_backend(),
        await _check_frontend(),
        await _check_heartbeat_service("bot", "Telegram бот", max_age=180.0),
        await _check_worker_fallback(),
        await _check_telegram_parser(),
    ]

    for source in WEB_PARSER_SOURCES:
        components.append(await _check_parser(source))

    return SystemStatus(components=components, checked_at=time.time())


def format_age_short(age: float | None) -> str:
    if age is None:
        return "—"
    if age < 90:
        return f"{int(age)} с"
    if age < 3600:
        return f"{int(age // 60)} хв"
    return f"{int(age // 3600)} год"


def format_status_message(status: SystemStatus, *, title: str = "Статус систем Carbit") -> str:
    level_icon = {
        HealthLevel.OK: "🟢",
        HealthLevel.DEGRADED: "🟡",
        HealthLevel.DOWN: "🔴",
        HealthLevel.UNKNOWN: "⚪️",
    }
    overall = status.overall
    lines = [
        f"<b>{title}</b>",
        f"{level_icon[overall]} Загалом: <b>{overall.value.upper()}</b>",
        f"🕐 {format_kyiv()}",
        "",
        "<b>Інфраструктура</b>",
    ]

    infra_ids = set(INFRA_COMPONENTS) | {"telegram_parser"}
    for comp in status.components:
        if comp.component_id not in infra_ids and not comp.component_id.startswith("parser:"):
            continue
        if comp.component_id.startswith("parser:"):
            continue
        icon = level_icon[comp.level]
        lines.append(f"{icon} <b>{comp.label}</b> — {comp.detail}")

    lines.extend(["", "<b>Парсери (6 джерел)</b>"])
    for comp in status.components:
        if not comp.component_id.startswith("parser:"):
            continue
        icon = level_icon[comp.level]
        lines.append(f"{icon} <b>{comp.label}</b> — {comp.detail}")

    problems = [c for c in status.components if c.level in {HealthLevel.DOWN, HealthLevel.DEGRADED}]
    if problems:
        lines.extend(["", "<b>Потребує уваги</b>"])
        for comp in problems:
            lines.append(f"• {comp.label}: {comp.detail}")

    return "\n".join(lines)
