"""Пруоризація апгрейду: кредит за невикористані дні поточного тарифу."""

from __future__ import annotations

import math

from app.core.timezone import as_kyiv, now_kyiv
from app.services.billing.plans import PLANS, get_plan

PLAN_ORDER = ("free", "lite", "standard", "pro")


def plan_rank(plan_id: str) -> int:
    try:
        return PLAN_ORDER.index(plan_id)
    except ValueError:
        return -1


def days_remaining(user) -> int:
    """Цілих днів доступу, що лишилися (мін. 0)."""
    expires = getattr(user, "plan_expires_at", None)
    if not expires:
        return 0
    delta = as_kyiv(expires) - now_kyiv()
    seconds = delta.total_seconds()
    if seconds <= 0:
        return 0
    return max(1, math.ceil(seconds / 86400))


def recommended_upgrade_plan(user) -> str | None:
    """Наступний платний план із більшим лімітом моніторингів."""
    current = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    # searches_limit на User враховує trial; інакше — каталог.
    current_limit = getattr(user, "searches_limit", None)
    if current_limit is None:
        current_limit = int(get_plan(current).get("searches_limit") or 0)
    else:
        current_limit = int(current_limit)
    for plan_id in PLAN_ORDER:
        if plan_id == "free" or plan_id == current:
            continue
        if plan_rank(plan_id) < plan_rank(current):
            continue
        plan = get_plan(plan_id)
        if int(plan.get("price_uah") or 0) <= 0:
            continue
        if int(plan.get("searches_limit") or 0) > current_limit:
            return plan_id
    return None


def compute_upgrade_quote(user, target_plan_id: str) -> dict:
    """
    Кредит = ціна_поточного * дні_залишку / період.
    Доплата = max(0, ціна_цільового − кредит) за новий повний період вищого тарифу.
    """
    if target_plan_id not in PLANS or target_plan_id == "free":
        raise ValueError("Невірний цільовий план")

    target = get_plan(target_plan_id)
    target_price = int(target.get("price_uah") or 0)
    if target_price <= 0:
        raise ValueError("Цільовий план безкоштовний")

    current_id = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    current = get_plan(current_id)
    current_price = int(current.get("price_uah") or 0)
    period_days = int(current.get("period_days") or 30) or 30
    target_period = int(target.get("period_days") or 30) or 30

    if current_id == target_plan_id:
        raise ValueError("Це вже ваш поточний тариф")

    paid_active = current_id != "free" and current_price > 0
    left = days_remaining(user) if paid_active else 0

    credit = 0
    if paid_active and left > 0:
        credit = int(round(current_price * left / period_days))

    amount_due = max(0, target_price - credit)
    # Рекурент лише коли платимо повну ціну (інакше LiqPay списував би знижку щомісяця).
    enable_subscribe = credit <= 0 or amount_due >= target_price

    return {
        "current_plan": current_id,
        "current_plan_name": current["name"],
        "current_price_uah": current_price,
        "target_plan": target_plan_id,
        "target_plan_name": target["name"],
        "target_price_uah": target_price,
        "target_searches_limit": int(target.get("searches_limit") or 0),
        "days_remaining": left,
        "period_days": period_days,
        "target_period_days": target_period,
        "credit_uah": credit,
        "amount_due_uah": amount_due,
        "enable_subscribe": enable_subscribe,
        "is_upgrade": plan_rank(target_plan_id) > plan_rank(current_id),
        "is_free_upgrade": amount_due <= 0,
    }
