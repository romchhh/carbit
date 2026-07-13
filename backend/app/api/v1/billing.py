from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user_id
from app.models.models import User
from app.schemas.schemas import PlanOut, SubscriptionOut, SubscribeRequest
from app.services.billing.plans import list_plans, get_plan, activate_plan, enforce_plan_expiry
from app.services.billing.notify import notify_plan_activated

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
async def get_plans():
    return list_plans()


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if enforce_plan_expiry(user):
        await db.flush()
    plan = get_plan(user.plan.value)
    return SubscriptionOut(
        plan=user.plan.value,
        plan_name=plan["name"],
        searches_limit=user.searches_limit,
        plan_expires_at=user.plan_expires_at,
        trial_ends_at=user.trial_ends_at,
        is_trial_active=user.is_trial_active,
    )


@router.post("/subscribe", response_model=SubscriptionOut)
async def subscribe(
    body: SubscribeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Зміна плану користувачем.
    Поки немає платіжки — дозволено лише downgrade на free.
    Платні плани активує адмін через /admin або внутрішній endpoint з DEBUG.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    if body.plan != "free" and not settings.DEBUG:
        raise HTTPException(
            402,
            "Оплата ще не підключена. Зверніться в підтримку або оберіть безкоштовний план.",
        )

    try:
        activate_plan(user, body.plan)
    except ValueError:
        raise HTTPException(400, "Unknown plan")
    await db.flush()
    plan = get_plan(user.plan.value)
    return SubscriptionOut(
        plan=user.plan.value,
        plan_name=plan["name"],
        searches_limit=user.searches_limit,
        plan_expires_at=user.plan_expires_at,
        trial_ends_at=user.trial_ends_at,
        is_trial_active=user.is_trial_active,
    )


@router.post("/admin/activate", response_model=SubscriptionOut)
async def admin_activate_plan(
    body: SubscribeRequest,
    target_user_id: str,
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Адмін вручну активує платний план (до інтеграції платежів)."""
    user = await db.get(User, target_user_id)
    if not user:
        raise HTTPException(404, "User not found")
    previous_plan = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    try:
        activate_plan(user, body.plan)
    except ValueError:
        raise HTTPException(400, "Unknown plan")
    await db.flush()
    await notify_plan_activated(db, user, previous_plan=previous_plan)
    plan = get_plan(user.plan.value)
    return SubscriptionOut(
        plan=user.plan.value,
        plan_name=plan["name"],
        searches_limit=user.searches_limit,
        plan_expires_at=user.plan_expires_at,
        trial_ends_at=user.trial_ends_at,
        is_trial_active=user.is_trial_active,
    )
