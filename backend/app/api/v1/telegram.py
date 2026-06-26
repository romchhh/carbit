from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_id, hash_password, create_access_token
from app.models.models import User
from app.schemas.schemas import (
    TelegramConnectLinkOut,
    TelegramStatusOut,
    TelegramRegisterInfoOut,
    TelegramRegisterCompleteRequest,
    TelegramRegisterCompleteOut,
)
from app.services.telegram.tokens import create_connect_token
from app.services.telegram.client import telegram_client
from app.services.telegram import tokens as tg_tokens
from app.services.telegram.links import bot_url, bot_username
from app.services.user_avatar import sync_telegram_avatar
from app.schemas.user import user_out

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/connect-link", response_model=TelegramConnectLinkOut)
async def get_connect_link(user_id: str = Depends(get_current_user_id)):
    token = await create_connect_token(user_id)
    username = bot_username()
    url = bot_url(f"connect_{token}")
    if not url:
        raise HTTPException(503, "Telegram bot not configured")
    return TelegramConnectLinkOut(
        bot_url=url,
        bot_username=username,
        expires_in=900,
    )


@router.get("/status", response_model=TelegramStatusOut)
async def telegram_status(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return TelegramStatusOut(
        connected=user.telegram_connected,
        telegram_username=user.telegram_username,
        telegram_id=user.telegram_id,
    )


@router.delete("/disconnect", status_code=204)
async def disconnect_telegram(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.telegram_id = None
    user.telegram_username = None
    user.telegram_avatar_path = None
    user.telegram_connected = False
    await db.flush()


@router.get("/register/{token}", response_model=TelegramRegisterInfoOut)
async def get_register_info(token: str):
    data = await tg_tokens.get_registration_token(token)
    if not data:
        return TelegramRegisterInfoOut(name="", email="", valid=False)
    return TelegramRegisterInfoOut(name=data["name"], email=data["email"], valid=True)


@router.post("/register/complete", response_model=TelegramRegisterCompleteOut)
async def complete_register(
    body: TelegramRegisterCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    data = await tg_tokens.get_registration_token(body.token)
    if not data:
        raise HTTPException(400, "Токен прострочений або недійсний")

    existing = await db.scalar(select(User).where(User.email == data["email"]))
    if existing:
        raise HTTPException(400, "Email already registered")

    tg_existing = await db.scalar(select(User).where(User.telegram_id == data["telegram_id"]))
    if tg_existing:
        raise HTTPException(400, "Telegram already linked to another account")

    user = User(
        email=data["email"],
        name=data["name"],
        hashed_password=hash_password(body.password),
        telegram_id=data["telegram_id"],
        telegram_username=data.get("username"),
        telegram_connected=True,
        trial_ends_at=User.default_trial_end(),
    )
    db.add(user)
    await db.flush()
    await sync_telegram_avatar(user)
    await db.flush()
    await tg_tokens.delete_registration_token(body.token)

    if data.get("chat_id"):
        await telegram_client.send_message(
            data["chat_id"],
            f"🎉 <b>Реєстрацію завершено!</b>\n\n"
            f"Ваш акаунт активний. Нові авто надходитимуть сюди.\n"
            f"Кабінет → {settings.FRONTEND_URL}/app/dashboard",
        )

    return TelegramRegisterCompleteOut(
        access_token=create_access_token(user.id),
        user=user_out(user),
    )
