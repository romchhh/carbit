import hmac

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User
from app.services.telegram import tokens as tg_tokens
from app.services.telegram.links import TELEGRAM_PLACEHOLDER_EMAIL_SUFFIX
from app.services.user_avatar import sync_telegram_avatar

router = APIRouter(prefix="/internal/bot", tags=["internal"])


class BotConnectRequest(BaseModel):
    token: str
    telegram_id: str
    telegram_username: str | None = None
    chat_id: str


class BotLoginRequest(BaseModel):
    telegram_id: str
    telegram_username: str | None = None
    chat_id: str


class BotRegisterRequest(BaseModel):
    telegram_id: str
    telegram_username: str | None = None
    chat_id: str
    name: str | None = None


class BotTelegramIdRequest(BaseModel):
    telegram_id: str


class BotMonitorRequest(BaseModel):
    telegram_id: str
    search_id: str


def verify_internal_secret(x_internal_secret: str = Header(...)):
    expected = settings.INTERNAL_API_SECRET or ""
    provided = x_internal_secret or ""
    if not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(403, "Forbidden")


@router.post("/connect")
async def bot_connect_telegram(
    body: BotConnectRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_internal_secret),
):
    user_id = await tg_tokens.consume_connect_token(body.token)
    if not user_id:
        return {"error": "token_expired"}

    existing = await db.scalar(select(User).where(User.telegram_id == body.telegram_id))
    if existing and existing.id != user_id:
        return {"error": "telegram_taken"}

    user = await db.get(User, user_id)
    if not user:
        return {"error": "user_not_found"}

    user.telegram_id = body.telegram_id
    user.telegram_username = body.telegram_username
    user.telegram_connected = True
    await sync_telegram_avatar(user)
    await db.flush()

    return {"success": True, "user_name": user.name, "user_id": user.id}


@router.post("/login")
async def bot_init_login(
    body: BotLoginRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_internal_secret),
):
    user = await db.scalar(select(User).where(User.telegram_id == body.telegram_id))
    if not user:
        return {"error": "not_registered"}

    if not user.is_active:
        return {"error": "account_deactivated"}

    await sync_telegram_avatar(user)
    await db.flush()

    token = await tg_tokens.create_login_token(user.id)
    login_url = f"{settings.FRONTEND_URL}/auth/telegram/login?token={token}"
    return {
        "success": True,
        "login_url": login_url,
        "user_name": user.name,
    }


@router.post("/register")
async def bot_init_register(
    body: BotRegisterRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_internal_secret),
):
    user = await db.scalar(select(User).where(User.telegram_id == body.telegram_id))
    if user:
        if not user.is_active:
            return {"error": "account_deactivated"}

        await sync_telegram_avatar(user)
        await db.flush()

        token = await tg_tokens.create_login_token(user.id)
        login_url = f"{settings.FRONTEND_URL}/auth/telegram/login?token={token}"
        return {
            "success": True,
            "already_registered": True,
            "login_url": login_url,
            "user_name": user.name,
        }

    name = (body.name or body.telegram_username or "Користувач").strip()
    email = f"tg{body.telegram_id}{TELEGRAM_PLACEHOLDER_EMAIL_SUFFIX}"

    token = await tg_tokens.create_registration_token(
        telegram_id=body.telegram_id,
        chat_id=body.chat_id,
        name=name,
        email=email,
        username=body.telegram_username,
    )
    register_url = f"{settings.FRONTEND_URL}/auth/telegram?token={token}"
    return {
        "success": True,
        "register_url": register_url,
        "user_name": name,
    }


@router.post("/subscription")
async def bot_subscription_status(
    body: BotTelegramIdRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_internal_secret),
):
    from app.models.models import BillingSubscription, SubscriptionStatus
    from app.services.billing.plans import enforce_plan_expiry, get_plan
    from app.services.billing.subscriptions import get_active_subscription

    user = await db.scalar(select(User).where(User.telegram_id == body.telegram_id))
    if not user:
        return {"error": "not_registered"}
    if not user.is_active:
        return {"error": "account_deactivated"}

    if enforce_plan_expiry(user):
        await db.flush()

    plan = get_plan(user.plan.value if hasattr(user.plan, "value") else str(user.plan))
    active = await get_active_subscription(db, user.id)
    past_due = None
    if not active:
        past_due = await db.scalar(
            select(BillingSubscription)
            .where(
                BillingSubscription.user_id == user.id,
                BillingSubscription.status == SubscriptionStatus.past_due,
            )
            .order_by(BillingSubscription.created_at.desc())
        )
    sub = active or past_due
    return {
        "success": True,
        "user_name": user.name,
        "plan": plan["id"],
        "plan_name": plan["name"],
        "searches_limit": user.searches_limit,
        "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
        "is_trial_active": bool(user.is_trial_active),
        "recurring_active": active is not None,
        "past_due": past_due is not None,
        "order_id": sub.order_id if sub else None,
        "failed_charges": int(getattr(sub, "failed_charges", 0) or 0) if sub else 0,
        "billing_url": f"{settings.FRONTEND_URL.rstrip('/')}/app/billing",
    }


@router.post("/monitor/info")
async def bot_monitor_info(
    body: BotMonitorRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_internal_secret),
):
    from app.models.models import SearchQuery
    from app.services.parser.filter_groups import search_monitor_display_name

    user = await db.scalar(select(User).where(User.telegram_id == body.telegram_id))
    if not user:
        return {"error": "not_registered"}
    if not user.is_active:
        return {"error": "account_deactivated"}

    sq = await db.get(SearchQuery, body.search_id)
    if not sq or sq.user_id != user.id:
        return {"error": "not_found"}

    return {
        "success": True,
        "search_name": search_monitor_display_name(sq),
        "is_active": bool(sq.is_active),
    }


@router.post("/monitor/deactivate")
async def bot_deactivate_monitor(
    body: BotMonitorRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_internal_secret),
):
    from app.models.models import SearchQuery
    from app.services.parser.filter_groups import search_monitor_display_name

    user = await db.scalar(select(User).where(User.telegram_id == body.telegram_id))
    if not user:
        return {"error": "not_registered"}
    if not user.is_active:
        return {"error": "account_deactivated"}

    sq = await db.get(SearchQuery, body.search_id)
    if not sq or sq.user_id != user.id:
        return {"error": "not_found"}

    label = search_monitor_display_name(sq)

    if not sq.is_active:
        return {
            "success": True,
            "already_inactive": True,
            "search_name": label,
            "message": f"Моніторинг «{label}» уже вимкнено.",
        }

    sq.is_active = False
    await db.flush()

    dashboard_url = f"{settings.FRONTEND_URL.rstrip('/')}/app/monitors"
    return {
        "success": True,
        "search_name": label,
        "message": f"Моніторинг «{label}» вимкнено. Нові сповіщення не надходитимуть.",
        "dashboard_url": dashboard_url,
    }


@router.post("/unsubscribe")
async def bot_unsubscribe(
    body: BotTelegramIdRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_internal_secret),
):
    from app.services.billing.notify import notify_subscription_cancelled
    from app.services.billing.plans import activate_plan, enforce_plan_expiry
    from app.services.billing.subscriptions import (
        cancel_active_subscriptions,
        get_active_subscription,
    )

    user = await db.scalar(select(User).where(User.telegram_id == body.telegram_id))
    if not user:
        return {"error": "not_registered"}
    if not user.is_active:
        return {"error": "account_deactivated"}

    if enforce_plan_expiry(user):
        await db.flush()

    active = await get_active_subscription(db, user.id)
    previous_plan = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    if not active and previous_plan == "free":
        return {
            "success": True,
            "already_free": True,
            "message": "Активної платної підписки немає.",
            "plan": "free",
            "plan_name": "Безкоштовний",
            "billing_url": f"{settings.FRONTEND_URL.rstrip('/')}/app/billing",
        }

    await cancel_active_subscriptions(db, user.id)
    if active is None and previous_plan != "free":
        activate_plan(user, "free")
    else:
        await notify_subscription_cancelled(db, user, reason="user")
    await db.flush()

    expires = user.plan_expires_at.isoformat() if user.plan_expires_at else None
    return {
        "success": True,
        "cancelled": True,
        "plan": user.plan.value if hasattr(user.plan, "value") else str(user.plan),
        "plan_expires_at": expires,
        "message": (
            "Автоплатіж скасовано. Доступ збережено до кінця оплаченого періоду."
            if expires
            else "Підписку скасовано."
        ),
        "billing_url": f"{settings.FRONTEND_URL.rstrip('/')}/app/billing",
    }
