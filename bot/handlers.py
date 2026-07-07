import logging

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend_api import init_telegram_login, init_telegram_register, link_telegram_account
from config import settings

logger = logging.getLogger(__name__)
router = Router()


def _user_meta(message: Message) -> tuple[str, str | None]:
    user = message.from_user
    if not user:
        raise ValueError("Missing sender")
    return str(user.id), user.username


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    if command.args and command.args.startswith("connect_"):
        token = command.args.removeprefix("connect_")
        telegram_id, username = _user_meta(message)
        await _handle_connect(message, token, telegram_id, username)
        return

    if command.args == "login":
        telegram_id, username = _user_meta(message)
        await _handle_login(message, telegram_id, username)
        return

    if command.args == "register":
        telegram_id, username = _user_meta(message)
        await _handle_register(message, telegram_id, username)
        return

    telegram_id, username = _user_meta(message)
    await _handle_register(message, telegram_id, username)


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Натисніть /start щоб почати роботу з Carbit.")


async def _handle_connect(
    message: Message,
    token: str,
    telegram_id: str,
    username: str | None,
) -> None:
    result = await link_telegram_account(token, telegram_id, username, str(message.chat.id))
    if not result:
        await message.answer(
            "⚠️ Не вдалося підключити. Посилання прострочене або вже використане.\n"
            "Згенеруйте нове в кабінеті → Акаунт → Telegram.",
        )
        return

    if result.get("error"):
        errors = {
            "token_expired": "⚠️ Посилання прострочене. Згенеруйте нове в кабінеті.",
            "telegram_taken": "⚠️ Цей Telegram вже прив'язаний до іншого акаунту.",
            "user_not_found": "⚠️ Акаунт не знайдено.",
        }
        await message.answer(errors.get(result["error"], "⚠️ Помилка підключення."))
        return

    await message.answer(
        f"✅ <b>Telegram підключено!</b>\n\n"
        f"Акаунт: {result.get('user_name', '')}\n"
        f"Тепер нові авто з ваших запитів надходитимуть сюди.\n\n"
        f"Кабінет → {settings.FRONTEND_URL}/app/dashboard",
    )


async def _handle_login(message: Message, telegram_id: str, username: str | None) -> None:
    result = await init_telegram_login(telegram_id, username, str(message.chat.id))
    if not result:
        await message.answer("⚠️ Не вдалося підключитись до сервера. Спробуйте пізніше.")
        return

    if result.get("error") == "not_registered":
        await _handle_register(message, telegram_id, username)
        return

    if result.get("error") == "account_deactivated":
        await message.answer("⚠️ Акаунт деактивовано. Зверніться до підтримки.")
        return

    login_url = result.get("login_url", "")
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔐 Увійти в кабінет", url=login_url)]],
    )
    await message.answer(
        f"Привіт, <b>{result.get('user_name', '')}</b>!\n\n"
        "Натисніть кнопку нижче, щоб увійти в Carbit.",
        reply_markup=markup,
    )


async def _handle_register(message: Message, telegram_id: str, username: str | None) -> None:
    user = message.from_user
    display_name = (
        (user.full_name if user and user.full_name else None)
        or (f"@{username}" if username else None)
        or "Користувач"
    )
    result = await init_telegram_register(
        telegram_id, username, str(message.chat.id), display_name
    )
    if not result:
        await message.answer("⚠️ Не вдалося підключитись до сервера. Спробуйте пізніше.")
        return

    if result.get("error") == "account_deactivated":
        await message.answer("⚠️ Акаунт деактивовано. Зверніться до підтримки.")
        return

    if result.get("already_registered"):
        login_url = result.get("login_url", "")
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔐 Увійти в кабінет", url=login_url)]],
        )
        await message.answer(
            f"Привіт, <b>{result.get('user_name', display_name)}</b>!\n\n"
            "У вас уже є акаунт. Натисніть кнопку, щоб увійти в кабінет.",
            reply_markup=markup,
        )
        return

    register_url = result.get("register_url", "")
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🚀 Відкрити кабінет", url=register_url)]],
    )
    await message.answer(
        f"👋 <b>Реєстрація в Carbit</b>\n\n"
        f"Привіт, <b>{result.get('user_name', display_name)}</b>!\n\n"
        "Натисніть кнопку нижче, щоб відкрити кабінет і завершити реєстрацію.",
        reply_markup=markup,
    )
