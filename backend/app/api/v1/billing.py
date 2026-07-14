from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user_id
from app.models.models import User
from app.schemas.schemas import (
    CheckoutOut,
    PlanOut,
    SubscribeRequest,
    SubscriptionOut,
    BillingPaymentOut,
)
from app.services.billing.liqpay import LiqPayNotConfiguredError, liqpay_configured
from app.services.billing.notify import notify_plan_activated
from app.services.billing.payments import list_user_payments
from app.services.billing.plans import activate_plan, enforce_plan_expiry, get_plan, list_plans
from app.services.billing.subscriptions import (
    cancel_active_subscriptions,
    create_checkout,
    get_active_subscription,
    handle_callback,
)

router = APIRouter(prefix="/billing", tags=["billing"])


def _format_card_mask(mask: str | None) -> str | None:
    if not mask:
        return None
    text = mask.strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 4:
        return f"•••• {digits[-4:]}"
    if "*" in text or "•" in text:
        return text
    return f"•••• {text[-4:]}" if len(text) >= 4 else text


async def _subscription_out(db, user) -> SubscriptionOut:
    plan = get_plan(user.plan.value)
    active = await get_active_subscription(db, user.id)
    payments = await list_user_payments(db, user.id, limit=20)
    payment_rows: list[BillingPaymentOut] = []
    for row in payments:
        payment_rows.append(
            BillingPaymentOut(
                id=row.id,
                order_id=row.order_id,
                plan=row.plan,
                plan_name=get_plan(row.plan).get("name") or row.plan,
                amount=int(row.amount or 0),
                currency=(row.currency or "UAH").upper(),
                status=row.status,
                card_mask=_format_card_mask(row.card_mask),
                description=row.description,
                paid_at=row.paid_at,
            )
        )

    next_payment = None
    if active and user.plan.value != "free" and user.plan_expires_at:
        next_payment = user.plan_expires_at

    return SubscriptionOut(
        plan=user.plan.value,
        plan_name=plan["name"],
        searches_limit=user.searches_limit,
        plan_expires_at=user.plan_expires_at,
        trial_ends_at=user.trial_ends_at,
        is_trial_active=user.is_trial_active,
        liqpay_enabled=liqpay_configured(),
        next_payment_at=next_payment,
        card_mask=_format_card_mask(active.card_mask if active else None),
        recurring_active=bool(active),
        payments=payment_rows,
    )


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
    return await _subscription_out(db, user)


@router.post("/checkout", response_model=CheckoutOut)
async def checkout(
    body: SubscribeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Створює LiqPay Checkout (subscribe) — фронт сабмітить форму на LiqPay."""
    if body.plan == "free":
        raise HTTPException(400, "Для Free плану використовуйте /billing/subscribe")
    if not liqpay_configured():
        raise HTTPException(
            503,
            "Оплата через LiqPay ще не налаштована. Зверніться в підтримку.",
        )
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    try:
        result = await create_checkout(db, user, body.plan)
    except LiqPayNotConfiguredError:
        raise HTTPException(503, "LiqPay не налаштовано")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    return CheckoutOut(**result)


@router.post("/subscribe", response_model=SubscriptionOut)
async def subscribe(
    body: SubscribeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Free — миттєвий downgrade (+ unsubscribe в LiqPay).
    Платні плани — через /billing/checkout (LiqPay).
    У DEBUG без ключів LiqPay — миттєва активація для локальної розробки.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    if body.plan != "free":
        if liqpay_configured():
            raise HTTPException(
                400,
                "Для платного плану використайте POST /billing/checkout",
            )
        if not settings.DEBUG:
            raise HTTPException(
                402,
                "Оплата ще не підключена. Зверніться в підтримку або оберіть безкоштовний план.",
            )

    previous_plan = user.plan.value if hasattr(user.plan, "value") else str(user.plan)

    if body.plan == "free":
        await cancel_active_subscriptions(db, user.id)

    try:
        activate_plan(user, body.plan)
    except ValueError:
        raise HTTPException(400, "Unknown plan")
    await db.flush()
    if body.plan != previous_plan:
        await notify_plan_activated(db, user, previous_plan=previous_plan)
    await db.commit()
    return await _subscription_out(db, user)


@router.post("/unsubscribe", response_model=SubscriptionOut)
async def unsubscribe(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Скасувати рекурент LiqPay і перейти на Free (доступ до кінця оплаченого періоду залишається)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    active = await get_active_subscription(db, user.id)
    previous_plan = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    await cancel_active_subscriptions(db, user.id)
    # Не зрізаємо одразу план — user користується до plan_expires_at
    if active is None and previous_plan != "free":
        # Немає LiqPay-підписки — просто даунгрейд
        activate_plan(user, "free")
        await notify_plan_activated(db, user, previous_plan=previous_plan)
    else:
        from app.services.billing.notify import notify_subscription_cancelled

        await notify_subscription_cancelled(db, user, reason="user")
    await db.commit()
    return await _subscription_out(db, user)


@router.post("/liqpay/callback")
async def liqpay_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    data: str | None = Form(None),
    signature: str | None = Form(None),
):
    """Публічний callback від LiqPay (без auth)."""
    if not data or not signature:
        # Іноді шлють application/x-www-form-urlencoded в body без Form binding
        form = await request.form()
        data = str(form.get("data") or "")
        signature = str(form.get("signature") or "")
    if not data or not signature:
        raise HTTPException(400, "Missing data/signature")
    try:
        result = await handle_callback(db, data, signature)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(400, str(exc)) from exc
    except Exception:
        await db.rollback()
        raise
    return JSONResponse(result)


@router.post("/admin/activate", response_model=SubscriptionOut)
async def admin_activate_plan(
    body: SubscribeRequest,
    target_user_id: str,
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Адмін вручну активує платний план."""
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
    await db.commit()
    return await _subscription_out(db, user)
