"""Сповіщення користувачу про зміну тарифу (адмінка / активація)."""

from __future__ import annotations

import logging
from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.timezone import as_kyiv
from app.models.models import Notification, NotificationType, User
from app.services.billing.plans import get_plan
from app.services.telegram.client import telegram_client

logger = logging.getLogger(__name__)


def _format_expires(user: User) -> str:
    if not user.plan_expires_at:
        return ""
    dt = as_kyiv(user.plan_expires_at)
    return dt.strftime("%d.%m.%Y")


async def notify_plan_activated(
    db: AsyncSession,
    user: User,
    *,
    previous_plan: str | None = None,
) -> bool:
    """
    Пише в Telegram (якщо підключено) і створює in-app notification.
    Повертає True, якщо Telegram-повідомлення відправлено.
    """
    plan = get_plan(user.plan.value if hasattr(user.plan, "value") else str(user.plan))
    plan_id = plan["id"]
    plan_name = plan["name"]
    searches = plan["searches_limit"]
    expires = _format_expires(user)
    cabinet = f"{settings.FRONTEND_URL.rstrip('/')}/app/billing"

    if plan_id == "free":
        title = "Тариф змінено на Безкоштовний"
        body = "Підписку вимкнено. Доступний 1 збережений пошук."
        tg_text = (
            "ℹ️ <b>Тариф оновлено</b>\n\n"
            "Активовано план <b>Безкоштовний</b>.\n"
            "Доступний 1 збережений пошук.\n\n"
            f"Кабінет → {cabinet}"
        )
    else:
        title = f"Підписку активовано: {plan_name}"
        until = f" до {expires}" if expires else ""
        body = (
            f"План «{plan_name}» активний{until}. "
            f"Ліміт пошуків: {searches}."
        )
        features = "\n".join(f"• {escape(f)}" for f in (plan.get("features") or [])[:4])
        tg_text = (
            f"🎉 <b>Підписку активовано!</b>\n\n"
            f"Тариф: <b>{escape(plan_name)}</b>\n"
            f"Ліміт пошуків: <b>{searches}</b>\n"
        )
        if expires:
            tg_text += f"Діє до: <b>{expires}</b>\n"
        if previous_plan and previous_plan != plan_id:
            prev_name = get_plan(previous_plan)["name"]
            tg_text += f"Було: {escape(prev_name)}\n"
        if features:
            tg_text += f"\n{features}\n"
        tg_text += f"\nКабінет → {cabinet}"

    notification = Notification(
        user_id=user.id,
        type=NotificationType.system,
        title=title,
        body=body,
        listing_id=None,
        search_id=None,
        payload={
            "event": "plan_activated",
            "plan": plan_id,
            "previous_plan": previous_plan,
            "searches_limit": searches,
            "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
        },
    )
    db.add(notification)

    sent = False
    if user.telegram_connected and user.telegram_id:
        try:
            result = await telegram_client.send_message(user.telegram_id, tg_text)
            if result:
                notification.sent_telegram = True
                sent = True
        except Exception:
            logger.exception(
                "Failed to send plan Telegram notify user=%s plan=%s",
                user.id,
                plan_id,
            )

    await db.flush()
    return sent
