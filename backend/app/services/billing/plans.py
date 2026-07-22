from datetime import timedelta

from app.core.timezone import as_kyiv, now_kyiv

PLANS: dict[str, dict] = {
    "free": {
        "id": "free",
        "name": "Безкоштовно",
        "description": "Пробний доступ на 7 днів",
        "searches_limit": 1,
        "accounts_limit": 1,
        "requests_month": 1_000,
        "requests_hour": 30,
        "price_uah": 0,
        "period_days": 7,
        "features": [
            "Пробний період 7 днів",
            "До 1 активного моніторингу",
            "1 акаунт",
            "Веб-кабінет і сповіщення",
        ],
    },
    "lite": {
        "id": "lite",
        "name": "Старт",
        "description": "До 10 активних моніторингів, 1 акаунт",
        "searches_limit": 10,
        "accounts_limit": 1,
        "requests_month": 50_000,
        "requests_hour": 2_000,
        "price_uah": 390,
        "period_days": 30,
        "features": [
            "30 днів доступу",
            "До 10 активних моніторингів",
            "1 акаунт",
            "Telegram-сповіщення",
            "Веб-кабінет",
        ],
    },
    "standard": {
        "id": "standard",
        "name": "Про",
        "description": "До 30 активних моніторингів, до 3 акаунтів",
        "searches_limit": 30,
        "accounts_limit": 3,
        "requests_month": 150_000,
        "requests_hour": 5_000,
        "price_uah": 790,
        "period_days": 30,
        "features": [
            "30 днів доступу",
            "До 30 активних моніторингів",
            "До 3 акаунтів",
            "Telegram-сповіщення",
            "Анти-дубль оголошень",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Бізнес",
        "description": "До 100 активних моніторингів, до 5 акаунтів",
        "searches_limit": 100,
        "accounts_limit": 5,
        "requests_month": 500_000,
        "requests_hour": 10_000,
        "price_uah": 1_790,
        "period_days": 30,
        "features": [
            "30 днів доступу",
            "До 100 активних моніторингів",
            "До 5 акаунтів",
            "Telegram-сповіщення",
            "Пріоритетна обробка пошуків",
        ],
    },
}

TRIAL_PLAN_ID = "lite"


def get_plan(plan_id: str) -> dict:
    return PLANS.get(plan_id, PLANS["free"])


def list_plans() -> list[dict]:
    return list(PLANS.values())


def effective_searches_limit(user) -> int:
    """Ліміт пошуків з урахуванням активного trial і expiry платного плану."""
    if enforce_plan_expiry(user):
        pass
    if getattr(user, "is_trial_active", False) and user.plan.value == "free":
        return get_plan(TRIAL_PLAN_ID)["searches_limit"]
    return get_plan(user.plan.value)["searches_limit"]


def enforce_plan_expiry(user) -> bool:
    """Downgrade expired paid plans to free. Returns True if changed."""
    from app.models.models import PlanTier

    if user.plan == PlanTier.free:
        return False
    expires = user.plan_expires_at
    if expires is None:
        return False
    if now_kyiv() < as_kyiv(expires):
        return False
    user.plan = PlanTier.free
    user.plan_expires_at = None
    return True


def admin_access_days(*, months: int | None = None, days: int | None = None) -> int:
    """Тривалість ручної видачі доступу з адмінки."""
    if days is not None:
        return max(1, int(days))
    if months is None:
        return 30
    m = max(1, int(months))
    if m == 12:
        return 365
    return m * 30


def _plan_expires_after(user, access_days: int):
    """Від max(зараз, поточний expiry) — щоб продовження не з’їдало оплачені дні."""
    base = now_kyiv()
    current = getattr(user, "plan_expires_at", None)
    if current is not None:
        exp = as_kyiv(current)
        if exp > base:
            base = exp
    return base + timedelta(days=access_days)


def activate_plan(
    user,
    plan_id: str,
    *,
    access_days: int | None = None,
    extend_from_current: bool = False,
) -> None:
    from app.models.models import PlanTier

    if plan_id not in PLANS:
        raise ValueError("Unknown plan")
    user.plan = PlanTier(plan_id)
    if plan_id == "free":
        user.plan_expires_at = None
    else:
        days = (
            access_days
            if access_days is not None
            else int(PLANS[plan_id].get("period_days") or 30)
        )
        if extend_from_current or access_days is not None:
            user.plan_expires_at = _plan_expires_after(user, days)
        else:
            user.plan_expires_at = now_kyiv() + timedelta(days=days)
