"""Сповіщення користувачу про зміну тарифу / проблеми з оплатою."""

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


def _cabinet_billing() -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/app/billing"


async def _push_system(
    db: AsyncSession,
    user: User,
    *,
    title: str,
    body: str,
    tg_text: str,
    payload: dict,
) -> bool:
    notification = Notification(
        user_id=user.id,
        type=NotificationType.system,
        title=title,
        body=body,
        listing_id=None,
        search_id=None,
        payload=payload,
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
                "Failed Telegram billing notify user=%s event=%s",
                user.id,
                payload.get("event"),
            )

    await db.flush()
    return sent


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
    cabinet = _cabinet_billing()

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

    return await _push_system(
        db,
        user,
        title=title,
        body=body,
        tg_text=tg_text,
        payload={
            "event": "plan_activated",
            "plan": plan_id,
            "previous_plan": previous_plan,
            "searches_limit": searches,
            "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
        },
    )


async def notify_payment_failed(
    db: AsyncSession,
    user: User,
    *,
    attempt: int,
    max_attempts: int,
    will_cancel: bool,
) -> bool:
    cabinet = _cabinet_billing()
    expires = _format_expires(user)
    if will_cancel:
        title = "Підписку скасовано через невдалу оплату"
        until = f" Доступ діє до {expires}." if expires else ""
        body = (
            f"Автосписання не вдалось {attempt} раз(и). "
            f"Рекурент скасовано.{until} Оновіть картку в кабінеті."
        )
        tg_text = (
            "⚠️ <b>Оплата не пройшла</b>\n\n"
            f"Невдалих спроб: <b>{attempt}/{max_attempts}</b>\n"
            "Автоматичні списання зупинено.\n"
        )
        if expires:
            tg_text += f"Платний доступ ще діє до <b>{expires}</b>.\n"
        tg_text += f"\nОновіть підписку → {cabinet}"
    else:
        title = "Не вдалось зняти оплату за підписку"
        body = (
            f"Спроба {attempt} з {max_attempts}. "
            "Перевірте картку — наступного разу може скасуватись автоплатіж."
        )
        tg_text = (
            "⚠️ <b>Проблема з оплатою</b>\n\n"
            f"Спроба <b>{attempt}</b> з <b>{max_attempts}</b> не вдалась.\n"
            "Перевірте картку. Якщо не вийде знову — рекурент зупинимо.\n\n"
            f"Кабінет → {cabinet}"
        )

    return await _push_system(
        db,
        user,
        title=title,
        body=body,
        tg_text=tg_text,
        payload={
            "event": "payment_failed",
            "attempt": attempt,
            "max_attempts": max_attempts,
            "will_cancel": will_cancel,
        },
    )


async def notify_subscription_cancelled(
    db: AsyncSession,
    user: User,
    *,
    reason: str = "user",
    note: str | None = None,
) -> bool:
    cabinet = _cabinet_billing()
    expires = _format_expires(user)
    until = f" Доступ збережено до {expires}." if expires else ""
    title = "Автоплатіж скасовано"
    body = f"Щомісячні списання зупинено.{until}"
    reason_line = {
        "user": "Скасовано вами.",
        "past_due": "Скасовано через невдалі оплати.",
        "expired": "Період підписки завершився.",
        "price": "Причина: занадто дорого.",
        "limits": "Причина: мало моніторингів / обмеження тарифу.",
        "results": "Причина: погано знаходить потрібні авто.",
        "usage": "Причина: рідко користуюся.",
        "tech": "Причина: технічні проблеми / незручний інтерфейс.",
        "other": "Причина: інше.",
    }.get(reason, f"Причина: {reason}." if reason else "Скасовано вами.")
    tg_text = (
        "🔕 <b>Автоплатіж скасовано</b>\n\n"
        f"{reason_line}\n"
    )
    if note and note.strip():
        safe_note = (
            note.strip()[:400]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        tg_text += f"Коментар: <i>{safe_note}</i>\n"
    if expires:
        tg_text += f"Платний доступ до: <b>{expires}</b>\n"
    else:
        tg_text += "План переведено на Безкоштовний.\n"
    tg_text += f"\nКабінет → {cabinet}"

    return await _push_system(
        db,
        user,
        title=title,
        body=body,
        tg_text=tg_text,
        payload={
            "event": "subscription_cancelled",
            "reason": reason,
            "note": (note or "").strip()[:500] or None,
        },
    )


async def notify_plan_expired(db: AsyncSession, user: User) -> bool:
    cabinet = _cabinet_billing()
    title = "Платний період завершився"
    body = "Тариф переведено на Безкоштовний. Оформіть підписку знову в кабінеті."
    tg_text = (
        "⌛ <b>Підписка закінчилась</b>\n\n"
        "Платний період завершився — активний план <b>Безкоштовний</b>.\n"
        f"Оформити знову → {cabinet}"
    )
    return await _push_system(
        db,
        user,
        title=title,
        body=body,
        tg_text=tg_text,
        payload={"event": "plan_expired"},
    )
