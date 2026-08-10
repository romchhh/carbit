from app.models.models import User
from app.schemas.schemas import UserOut
from app.services.user_avatar import user_avatar_api_path
from app.services.telegram.links import is_placeholder_email
from app.services.phone.normalize import format_phone_display, is_phone_placeholder_email


def user_out(user: User) -> UserOut:
    data = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "plan": user.plan.value if hasattr(user.plan, "value") else str(user.plan),
        "searches_limit": user.searches_limit,
        "telegram_connected": bool(user.telegram_connected),
        "telegram_username": user.telegram_username,
        "avatar_url": None,
        "email_verified": False,
        "phone": None,
        "phone_verified": False,
        "has_password": bool(user.hashed_password),
        "trial_ends_at": user.trial_ends_at,
        "is_trial_active": bool(user.is_trial_active),
        "onboarding_completed": bool(user.onboarding_completed),
        "plan_expires_at": user.plan_expires_at,
        "preferred_currency": getattr(user, "preferred_currency", None) or "UAH",
        "created_at": user.created_at,
    }
    out = UserOut.model_validate(data)
    out.avatar_url = user_avatar_api_path(user)
    if is_placeholder_email(user.email) or is_phone_placeholder_email(user.email):
        out.email = ""
        out.email_verified = False
    else:
        out.email_verified = True
    if getattr(user, "phone_verified_at", None) and user.phone:
        out.phone = format_phone_display(user.phone)
        out.phone_verified = True
    return out
