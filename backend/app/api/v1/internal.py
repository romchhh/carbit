from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User
from app.services.telegram import tokens as tg_tokens
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


def verify_internal_secret(x_internal_secret: str = Header(...)):
    if x_internal_secret != settings.INTERNAL_API_SECRET:
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

    token = await tg_tokens.create_login_token(user.id)
    login_url = f"{settings.FRONTEND_URL}/auth/telegram/login?token={token}"
    return {
        "success": True,
        "login_url": login_url,
        "user_name": user.name,
    }
