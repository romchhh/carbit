from datetime import timedelta

from app.core.timezone import as_kyiv, now_kyiv

SIGNUP_TRIAL_DAYS = 7
SIGNUP_TRIAL_PLAN_ID = "lite"

PLANS: dict[str, dict] = {
    "free": {
        "id": "free",
        "name": "Безкоштовно",
        "description": "Базовий доступ після пробного «Старт»",
        "searches_limit": 1,
        "devices_limit": 1,
        "requests_month": 1_000,
        "requests_hour": 90,
        # Live-пошук у кабінеті: лише нові запити (page=1), не пагінація.
        "live_searches_hour": 30,
        "vin_checks_limit": None,
        "price_uah": 0,
        "period_days": 0,
        "features": [
            "1 активний моніторинг",
            "Необмежені перевірки VIN",
            "1 пристрій",
            "Веб-кабінет і сповіщення",
        ],
    },
    "lite": {
        "id": "lite",
        "name": "Старт",
        "description": "До 10 активних моніторингів, до 2 пристроїв",
        "searches_limit": 10,
        "devices_limit": 2,
        "requests_month": 50_000,
        "requests_hour": 6_000,
        "live_searches_hour": 150,
        "vin_checks_limit": None,
        "price_uah": 390,
        "period_days": 30,
        "features": [
            "30 днів доступу",
            "До 10 активних моніторингів",
            "Необмежені перевірки VIN",
            "До 2 пристроїв",
            "Telegram-сповіщення",
            "Веб-кабінет",
        ],
    },
    "standard": {
        "id": "standard",
        "name": "Про",
        "description": "До 30 активних моніторингів, до 6 пристроїв",
        "searches_limit": 30,
        "devices_limit": 6,
        "requests_month": 150_000,
        "requests_hour": 15_000,
        "live_searches_hour": 300,
        "vin_checks_limit": None,
        "price_uah": 790,
        "period_days": 30,
        "features": [
            "30 днів доступу",
            "До 30 активних моніторингів",
            "Необмежені перевірки VIN",
            "До 6 пристроїв",
            "Telegram-сповіщення",
            "Анти-дубль оголошень",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Бізнес",
        "description": "До 100 активних моніторингів, до 12 пристроїв",
        "searches_limit": 100,
        "devices_limit": 12,
        "requests_month": 500_000,
        "requests_hour": 30_000,
        "live_searches_hour": 600,
        "vin_checks_limit": None,
        "price_uah": 1_790,
        "period_days": 30,
        "features": [
            "30 днів доступу",
            "До 100 активних моніторингів",
            "Необмежені перевірки VIN",
            "До 12 пристроїв",
            "Telegram-сповіщення",
            "Пріоритетна обробка пошуків",
        ],
    },
}

def get_plan(plan_id: str) -> dict:
    return PLANS.get(plan_id, PLANS["free"])


def list_plans() -> list[dict]:
    return list(PLANS.values())


def effective_searches_limit(user) -> int:
    """Ліміт моніторингів з урахуванням expiry платного плану."""
    if enforce_plan_expiry(user):
        pass
    return get_plan(user.plan.value)["searches_limit"]


def effective_devices_limit(user) -> int:
    """Скільки одночасних сесій (пристроїв) дозволяє план."""
    if enforce_plan_expiry(user):
        pass
    return max(1, int(get_plan(user.plan.value).get("devices_limit") or 1))


def effective_live_searches_hour(user) -> int:
    """Скільки нових live-пошуків (page=1) на годину дозволяє план."""
    if enforce_plan_expiry(user):
        pass
    plan = get_plan(user.plan.value)
    return max(1, int(plan.get("live_searches_hour") or 30))


async def enforce_active_searches_quota(db, user) -> int:
    """Після кінця trial / downgrade — лишає лише N найстаріших активних моніторингів.

    Повертає кількість призупинених. Без цього ліміт у UI падає до 1,
    а зайві моніторинги з пробного періоду лишаються активними.
    """
    from sqlalchemy import select

    from app.models.models import SearchQuery

    limit = max(0, int(effective_searches_limit(user)))
    rows = await db.scalars(
        select(SearchQuery)
        .where(SearchQuery.user_id == user.id, SearchQuery.is_active.is_(True))
        .order_by(SearchQuery.created_at.asc())
    )
    active = list(rows.all())
    if len(active) <= limit:
        return 0

    paused = 0
    for sq in active[limit:]:
        sq.is_active = False
        paused += 1
    if paused:
        await db.flush()
    return paused


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
    trial_end = getattr(user, "trial_ends_at", None)
    if trial_end is not None and now_kyiv() >= as_kyiv(trial_end):
        user.trial_ends_at = None
    return True


def grant_signup_trial(user) -> None:
    """7 днів «Старт» після реєстрації; далі — Free через expire_paid_plans."""
    activate_plan(user, SIGNUP_TRIAL_PLAN_ID, access_days=SIGNUP_TRIAL_DAYS)
    user.trial_ends_at = now_kyiv() + timedelta(days=SIGNUP_TRIAL_DAYS)


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
