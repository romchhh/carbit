import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth_cookies import AUTH_COOKIE_MAX_AGE, AUTH_COOKIE_NAME, attach_auth_cookie, clear_auth_cookie
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    get_current_user_id,
    get_current_user_id_flexible,
    _decode_user_token,
    _extract_bearer_or_cookie,
    optional_bearer,
)
from app.core.token_response import token_json_response
from app.services.auth.sessions import issue_user_access_token, revoke_session
from app.models.models import User
from app.schemas.schemas import (
    RegisterRequest,
    VerifyCodeRequest,
    ResendCodeRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    PhoneSendCodeRequest,
    PhoneVerifyRequest,
    PhonePasswordLoginRequest,
    SetPasswordRequest,
    TelegramLoginRequest,
    TelegramLoginUrlOut,
    TokenResponse,
    UserOut,
    UserProfileUpdate,
    MessageResponse,
)
from app.services import verification as verify_svc
from app.services import password_reset as pwd_reset_svc
from app.services import google_oauth as google_svc
from app.services.email import send_verification_code, send_welcome_email, send_password_reset_email
from app.services.rate_limit import client_ip, enforce_rate_limit
from app.services.telegram import tokens as tg_tokens
from app.services.telegram.client import telegram_client
from app.services.telegram.links import bot_url, bot_username
from app.services.user_avatar import sync_telegram_avatar
from app.schemas.user import user_out
from app.services.phone.normalize import PhoneValidationError, normalize_ua_phone, phone_placeholder_email
from app.services.phone import verification as phone_verify_svc
from app.services.phone.users import get_verified_phone_user, is_phone_taken
from app.services.phone.delivery import PhoneCodeDeliveryError, deliver_phone_auth_code
from app.core.timezone import now_kyiv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/send-code", response_model=MessageResponse)
async def register_send_code(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await enforce_rate_limit(
        key=f"register:{client_ip(request)}",
        limit=10,
        window_seconds=3600,
        detail="Занадто багато реєстрацій з цієї IP. Спробуйте пізніше.",
    )
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if not await verify_svc.resend_allowed(body.email):
        raise HTTPException(status_code=429, detail="Зачекайте хвилину перед повторною відправкою")
    hashed = hash_password(body.password)
    code = await verify_svc.store_registration(body.email, body.name, hashed)

    try:
        await send_verification_code(body.email, body.name, code)
    except Exception:
        logger.exception("Failed to send verification email to %s", body.email)
        raise HTTPException(status_code=502, detail="Не вдалося надіслати лист. Спробуйте пізніше")

    return MessageResponse(message="Код підтвердження надіслано на email", expires_in=verify_svc.CODE_TTL)


@router.post("/register/resend-code", response_model=MessageResponse)
async def register_resend_code(body: ResendCodeRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    pending = await verify_svc.get_registration(body.email)
    if not pending:
        raise HTTPException(status_code=400, detail="Реєстрація не знайдена. Почніть спочатку")

    if not await verify_svc.resend_allowed(body.email):
        raise HTTPException(status_code=429, detail="Зачекайте хвилину перед повторною відправкою")

    code = await verify_svc.refresh_code(body.email)
    if not code:
        raise HTTPException(status_code=400, detail="Реєстрація не знайдена. Почніть спочатку")

    try:
        await send_verification_code(body.email, pending["name"], code)
    except Exception:
        logger.exception("Failed to resend verification email to %s", body.email)
        raise HTTPException(status_code=502, detail="Не вдалося надіслати лист. Спробуйте пізніше")

    return MessageResponse(message="Новий код надіслано", expires_in=verify_svc.CODE_TTL)


@router.post("/register/verify", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_verify(body: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    data = await verify_svc.verify_code(body.email, body.code)
    if not data:
        raise HTTPException(status_code=400, detail="Невірний або прострочений код")

    user = User(
        email=body.email,
        name=data["name"],
        hashed_password=data["hashed_password"],
        trial_ends_at=User.default_trial_end(),
    )
    db.add(user)
    await db.flush()

    try:
        await send_welcome_email(body.email, data["name"])
    except Exception:
        logger.exception("Failed to send welcome email to %s", body.email)

    return token_json_response(await issue_user_access_token(user), status_code=status.HTTP_201_CREATED)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await enforce_rate_limit(
        key=f"login:{client_ip(request)}:{body.email.lower()}",
        limit=20,
        window_seconds=900,
        detail="Занадто багато спроб входу. Спробуйте через 15 хвилин.",
    )
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    max_age = AUTH_COOKIE_MAX_AGE if body.remember else None
    return token_json_response(await issue_user_access_token(user), max_age=max_age)


@router.post("/phone/send-code", response_model=MessageResponse)
async def phone_send_code(
    body: PhoneSendCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        phone = normalize_ua_phone(body.phone)
    except PhoneValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    intent = body.intent.strip().lower()
    if intent not in ("login", "register"):
        raise HTTPException(status_code=400, detail="Невірний intent")

    await enforce_rate_limit(
        key=f"phone_auth:{client_ip(request)}:{phone}",
        limit=8,
        window_seconds=3600,
        detail="Занадто багато спроб. Спробуйте пізніше.",
    )

    existing = await get_verified_phone_user(db, phone)

    if intent == "login":
        if not existing:
            raise HTTPException(status_code=404, detail="Номер не зареєстровано. Створіть акаунт.")
    else:
        if existing:
            raise HTTPException(status_code=400, detail="Цей номер вже зареєстровано. Увійдіть.")
        name = (body.name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Вкажіть ім'я для реєстрації")

    if not await phone_verify_svc.phone_auth_resend_allowed(phone):
        raise HTTPException(status_code=429, detail="Зачекайте хвилину перед повторною відправкою")

    code = await phone_verify_svc.store_phone_auth(
        phone,
        intent=intent,
        name=(body.name or "").strip() or None,
    )

    delivery = (body.delivery or "auto").strip().lower()
    if intent == "register":
        delivery = "sms"

    try:
        message, channel = await deliver_phone_auth_code(
            phone=phone,
            code=code,
            intent=intent,
            user=existing if intent == "login" else None,
            delivery=delivery,
        )
    except PhoneCodeDeliveryError as exc:
        logger.exception("Failed to deliver auth code to %s", phone)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to deliver auth code to %s", phone)
        raise HTTPException(status_code=502, detail="Не вдалося надіслати код. Спробуйте пізніше.") from exc

    return MessageResponse(
        message=message,
        expires_in=phone_verify_svc.CODE_TTL,
        channel=channel,
    )


@router.post("/phone/verify", response_model=TokenResponse)
async def phone_verify(
    body: PhoneVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        phone = normalize_ua_phone(body.phone)
    except PhoneValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    intent = body.intent.strip().lower()
    data = await phone_verify_svc.verify_phone_auth(phone, body.code, intent=intent)
    if not data:
        raise HTTPException(status_code=400, detail="Невірний або прострочений код")

    if intent == "login":
        user = await get_verified_phone_user(db, phone)
        if not user:
            raise HTTPException(status_code=404, detail="Номер не зареєстровано")
    else:
        if await is_phone_taken(db, phone):
            raise HTTPException(status_code=400, detail="Цей номер вже зареєстровано")

        name = (body.name or data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Вкажіть ім'я для реєстрації")

        user = User(
            email=phone_placeholder_email(phone),
            name=name,
            phone=phone,
            phone_verified_at=now_kyiv(),
            trial_ends_at=User.default_trial_end(),
        )
        db.add(user)
        await db.flush()

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    max_age = AUTH_COOKIE_MAX_AGE if body.remember else None
    status_code = status.HTTP_201_CREATED if intent == "register" else status.HTTP_200_OK
    return token_json_response(await issue_user_access_token(user), max_age=max_age, status_code=status_code)


@router.post("/phone/login", response_model=TokenResponse)
async def phone_password_login(
    body: PhonePasswordLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        phone = normalize_ua_phone(body.phone)
    except PhoneValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await enforce_rate_limit(
        key=f"phone_login:{client_ip(request)}:{phone}",
        limit=20,
        window_seconds=900,
        detail="Занадто багато спроб входу. Спробуйте через 15 хвилин.",
    )

    user = await get_verified_phone_user(db, phone)
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Невірний номер або пароль")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    max_age = AUTH_COOKIE_MAX_AGE if body.remember else None
    return token_json_response(await issue_user_access_token(user), max_age=max_age)


@router.post("/password/set", response_model=UserOut)
async def set_password(
    body: SetPasswordRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.hashed_password:
        if not body.current_password or not verify_password(body.current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Невірний поточний пароль")

    user.hashed_password = hash_password(body.password)
    await db.flush()
    return user_out(user)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    cookie_token: str | None = Cookie(None, alias=AUTH_COOKIE_NAME),
):
    """Знімає HttpOnly cookie і відкликає поточну сесію."""
    token = _extract_bearer_or_cookie(credentials, cookie_token)
    if token:
        try:
            user_id, jti = _decode_user_token(token)
            if jti:
                await revoke_session(user_id, jti)
        except Exception:
            logger.debug("Logout session revoke skipped", exc_info=True)

    response = JSONResponse(content={"message": "ok"})
    clear_auth_cookie(response)
    return response


class OAuthExchangeRequest(BaseModel):
    code: str = Field(min_length=16, max_length=256)


@router.post("/oauth/exchange", response_model=TokenResponse)
async def oauth_exchange(body: OAuthExchangeRequest):
    token = await google_svc.consume_login_code(body.code)
    if not token:
        raise HTTPException(status_code=400, detail="Код недійсний або прострочений")
    return token_json_response(token)

@router.post("/password/forgot", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email))
    if user and await pwd_reset_svc.resend_allowed(body.email):
        token = await pwd_reset_svc.create_reset_token(user.id, user.email)
        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
        try:
            await send_password_reset_email(user.email, user.name, reset_url)
        except Exception:
            logger.exception("Failed to send password reset email to %s", user.email)
        await pwd_reset_svc.set_cooldown(body.email)
    elif user:
        raise HTTPException(status_code=429, detail="Зачекайте хвилину перед повторною відправкою")

    return MessageResponse(
        message="Якщо акаунт з таким email існує, ми надіслали інструкції для скидання пароля",
        expires_in=pwd_reset_svc.RESET_TTL,
    )


@router.post("/password/reset", response_model=TokenResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    data = await pwd_reset_svc.consume_reset_token(body.token)
    if not data:
        raise HTTPException(status_code=400, detail="Посилання прострочене або недійсне")

    user = await db.get(User, data["user_id"])
    if not user or user.email != data["email"]:
        raise HTTPException(status_code=400, detail="Посилання прострочене або недійсне")

    user.hashed_password = hash_password(body.password)
    await db.flush()
    return token_json_response(await issue_user_access_token(user))


@router.get("/google")
async def google_login():
    if not google_svc.is_configured():
        raise HTTPException(status_code=503, detail="Google OAuth не налаштовано")
    state = await google_svc.create_state()
    return RedirectResponse(google_svc.build_authorize_url(state))


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if error or not code or not state:
        params = urlencode({"error": error or "access_denied"})
        return RedirectResponse(f"{settings.FRONTEND_URL}/auth/oauth/callback?{params}")

    if not await google_svc.verify_state(state):
        params = urlencode({"error": "invalid_state"})
        return RedirectResponse(f"{settings.FRONTEND_URL}/auth/oauth/callback?{params}")

    try:
        profile = await google_svc.exchange_code(code)
    except Exception:
        logger.exception("Google OAuth exchange failed")
        params = urlencode({"error": "oauth_failed"})
        return RedirectResponse(f"{settings.FRONTEND_URL}/auth/oauth/callback?{params}")

    google_id = profile.get("sub")
    email = profile.get("email")
    name = profile.get("name") or (email.split("@")[0] if email else "Користувач")

    if not google_id or not email:
        params = urlencode({"error": "profile_incomplete"})
        return RedirectResponse(f"{settings.FRONTEND_URL}/auth/oauth/callback?{params}")

    user = await db.scalar(select(User).where(User.google_id == google_id))
    if not user:
        user = await db.scalar(select(User).where(User.email == email))
        if user:
            if not user.google_id:
                user.google_id = google_id
        else:
            user = User(
                email=email,
                name=name,
                google_id=google_id,
                trial_ends_at=User.default_trial_end(),
            )
            db.add(user)
            await db.flush()

    if not user.is_active:
        params = urlencode({"error": "account_deactivated"})
        return RedirectResponse(f"{settings.FRONTEND_URL}/auth/oauth/callback?{params}")

    token = await issue_user_access_token(user)
    login_code = await google_svc.create_login_code(token)
    params = urlencode({"code": login_code})
    response = RedirectResponse(f"{settings.FRONTEND_URL}/auth/oauth/callback?{params}")
    attach_auth_cookie(response, token)
    return response

@router.get("/telegram/login-url", response_model=TelegramLoginUrlOut)
async def telegram_login_url():
    username = bot_username()
    url = bot_url("login")
    if not url:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Telegram bot not configured")
    return TelegramLoginUrlOut(
        bot_url=url,
        bot_username=username,
    )


@router.get("/telegram/register-url", response_model=TelegramLoginUrlOut)
async def telegram_register_url():
    username = bot_username()
    url = bot_url("register")
    if not url:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Telegram bot not configured")
    return TelegramLoginUrlOut(
        bot_url=url,
        bot_username=username,
    )


@router.post("/telegram/login", response_model=TokenResponse)
async def telegram_login(body: TelegramLoginRequest, db: AsyncSession = Depends(get_db)):
    user_id = await tg_tokens.consume_login_token(body.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Посилання прострочене або недійсне")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Акаунт не знайдено")

    return token_json_response(await issue_user_access_token(user))


@router.get("/me", response_model=UserOut)
async def me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from app.services.billing.plans import enforce_active_searches_quota

    await enforce_active_searches_quota(db, user)

    if user.telegram_connected and user.telegram_id:
        await sync_telegram_avatar(user)
        await db.flush()

    return user_out(user)


@router.get("/me/avatar")
async def me_avatar(
    user_id: str = Depends(get_current_user_id_flexible),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Avatar not found")

    if user.telegram_connected and user.telegram_id:
        await sync_telegram_avatar(user)
        await db.flush()

    if not user.telegram_avatar_path:
        raise HTTPException(status_code=404, detail="Avatar not found")

    content = await telegram_client.get_file_bytes(user.telegram_avatar_path)
    if not content:
        await sync_telegram_avatar(user)
        await db.flush()
        if user.telegram_avatar_path:
            content = await telegram_client.get_file_bytes(user.telegram_avatar_path)
    if not content:
        raise HTTPException(status_code=404, detail="Avatar not found")

    media_type = "image/jpeg"
    if user.telegram_avatar_path.lower().endswith(".png"):
        media_type = "image/png"
    elif user.telegram_avatar_path.lower().endswith(".webp"):
        media_type = "image/webp"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: UserProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.name is None and body.preferred_currency is None:
        raise HTTPException(status_code=400, detail="Немає змін для збереження")

    if body.name is not None:
        user.name = body.name
    if body.preferred_currency is not None:
        user.preferred_currency = body.preferred_currency
    try:
        await db.flush()
    except Exception as exc:
        logger.exception("Failed to update profile for %s", user_id)
        raise HTTPException(
            status_code=500,
            detail="Не вдалося зберегти профіль. Спробуйте після оновлення сервера.",
        ) from exc
    return user_out(user)
