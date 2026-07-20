"""Окремий Telegram-бот підтримки: повідомлення користувачів → адмін, відповіді назад."""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import settings

logger = logging.getLogger(__name__)
router = Router()

# message_id у чаті адміна → telegram user id клієнта
_pending_replies: dict[int, int] = {}


def _admin_id() -> int | None:
    raw = settings.admin_chat_id
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 <b>Підтримка Carbit</b>\n\n"
        "Напишіть своє питання — ми відповімо тут у чаті.\n"
        "Типові теми: тариф, оплата, моніторинги, Telegram-сповіщення.\n\n"
        f"Кабінет: {settings.FRONTEND_URL}/app/account",
    )


@router.message(F.chat.type == "private", F.text | F.photo | F.document | F.voice | F.video)
async def user_to_support(message: Message, bot: Bot) -> None:
    admin = _admin_id()
    if not admin:
        await message.answer("⚠️ Підтримка тимчасово недоступна. Спробуйте пізніше.")
        logger.error("TELEGRAM_SUPPORT_ADMIN_CHAT_ID / TELEGRAM_ADMIN_CHAT_ID not set")
        return

    if message.from_user and message.from_user.id == admin:
        return

    user = message.from_user
    if not user:
        return

    username = f"@{user.username}" if user.username else "без username"
    name = (user.full_name or "").strip() or "Користувач"
    header = (
        f"📩 <b>Звернення в підтримку</b>\n"
        f"{name} ({username})\n"
        f"id: <code>{user.id}</code>\n"
        f"↩ Відповісти reply на це повідомлення"
    )

    try:
        meta = await bot.send_message(admin, header)
        forwarded = await message.forward(admin)
        _pending_replies[meta.message_id] = user.id
        _pending_replies[forwarded.message_id] = user.id
        await message.answer("✅ Повідомлення надіслано в підтримку. Очікуйте відповіді тут.")
    except Exception:
        logger.exception("Failed to forward support message")
        await message.answer("⚠️ Не вдалося надіслати. Спробуйте ще раз через хвилину.")


@router.message(F.reply_to_message)
async def admin_reply(message: Message, bot: Bot) -> None:
    admin = _admin_id()
    if not admin or message.chat.id != admin:
        return

    reply = message.reply_to_message
    if not reply:
        return

    user_id = _pending_replies.get(reply.message_id)
    if user_id is None and reply.forward_from:
        user_id = reply.forward_from.id
    if user_id is None:
        await message.answer("Не знайдено користувача для відповіді. Reply на службове повідомлення.")
        return

    try:
        if message.text:
            await bot.send_message(user_id, f"💬 <b>Підтримка Carbit</b>\n\n{message.html_text or message.text}")
        else:
            await message.copy_to(user_id)
        await message.answer("✅ Відповідь надіслано клієнту")
    except Exception:
        logger.exception("Failed to send support reply to %s", user_id)
        await message.answer("⚠️ Не вдалося доставити відповідь")
