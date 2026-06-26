from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import User
from app.schemas.schemas import PlanOut, SubscriptionOut, SubscribeRequest
from app.services.billing.plans import list_plans, get_plan, activate_plan

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
    """Mock subscription change (payment gateway integration later)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
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
