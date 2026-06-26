import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user_id, get_current_user_id_flexible
from app.models.models import User
from app.schemas.schemas import (
    RegisterRequest,
    VerifyCodeRequest,
    ResendCodeRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
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
from app.services.telegram import tokens as tg_tokens
from app.services.telegram.client import telegram_client
from app.services.telegram.links import bot_url, bot_username
from app.services.user_avatar import sync_telegram_avatar
from app.schemas.user import user_out

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/send-code", response_model=MessageResponse)
async def register_send_code(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
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

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    return TokenResponse(access_token=create_access_token(user.id))


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
    return TokenResponse(access_token=create_access_token(user.id))


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

    token = create_access_token(user.id)
    params = urlencode({"token": token})
    return RedirectResponse(f"{settings.FRONTEND_URL}/auth/oauth/callback?{params}")


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

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.telegram_connected and user.telegram_id and user.telegram_avatar_path is None:
        await sync_telegram_avatar(user)
        await db.flush()

    return user_out(user)


@router.get("/me/avatar")
async def me_avatar(
    user_id: str = Depends(get_current_user_id_flexible),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user or not user.telegram_avatar_path:
        raise HTTPException(status_code=404, detail="Avatar not found")

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

    user.name = body.name
    await db.flush()
    return user_out(user)
