from datetime import timedelta

from app.core.timezone import as_kyiv, now_kyiv

PLANS: dict[str, dict] = {
    "free": {
        "id": "free",
        "name": "Безкоштовно",
        "description": "Для ознайомлення з сервісом",
        "searches_limit": 1,
        "requests_month": 1_000,
        "requests_hour": 30,
        "price_uah": 0,
        "features": ["1 пошуковий запит", "Telegram-сповіщення", "3 дні trial Pro (ліміт пошуків Pro)"],
    },
    "lite": {
        "id": "lite",
        "name": "Lite",
        "description": "Для перекупників-початківців",
        "searches_limit": 3,
        "requests_month": 20_000,
        "requests_hour": 2_000,
        "price_uah": 500,
        "features": ["3 пошукові запити", "Швидкі сповіщення", "Ризик-оцінка"],
    },
    "standard": {
        "id": "standard",
        "name": "Стандарт",
        "description": "Для підбору одного авто",
        "searches_limit": 10,
        "requests_month": 100_000,
        "requests_hour": 5_000,
        "price_uah": 2_000,
        "features": ["10 пошукових запитів", "Пріоритетні сповіщення", "Експорт CSV"],
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "description": "Для професійних підбірників",
        "searches_limit": 50,
        "requests_month": 500_000,
        "requests_hour": 10_000,
        "price_uah": 6_000,
        "features": ["50 пошукових запитів", "Миттєві сповіщення", "API доступ (незабаром)"],
    },
}

TRIAL_PLAN_ID = "pro"


def get_plan(plan_id: str) -> dict:
    return PLANS.get(plan_id, PLANS["free"])


def list_plans() -> list[dict]:
    return list(PLANS.values())


def effective_searches_limit(user) -> int:
    """Ліміт пошуків з урахуванням активного trial Pro і expiry платного плану."""
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


def activate_plan(user, plan_id: str) -> None:
    from app.models.models import PlanTier

    if plan_id not in PLANS:
        raise ValueError("Unknown plan")
    user.plan = PlanTier(plan_id)
    if plan_id == "free":
        user.plan_expires_at = None
    else:
        user.plan_expires_at = now_kyiv() + timedelta(days=30)
