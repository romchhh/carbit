import logging
import re

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend_api import init_telegram_login, link_telegram_account
from config import settings
from states import Registration
import tokens as tg_tokens

logger = logging.getLogger(__name__)
router = Router()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _user_meta(message: Message) -> tuple[str, str | None]:
    user = message.from_user
    if not user:
        raise ValueError("Missing sender")
    return str(user.id), user.username


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext) -> None:
    if command.args and command.args.startswith("connect_"):
        token = command.args.removeprefix("connect_")
        telegram_id, username = _user_meta(message)
        await _handle_connect(message, token, telegram_id, username)
        return

    if command.args == "login":
        telegram_id, username = _user_meta(message)
        await _handle_login(message, telegram_id, username)
        return

    telegram_id, username = _user_meta(message)
    await state.clear()
    await state.update_data(telegram_id=telegram_id, username=username)
    await state.set_state(Registration.name)
    await message.answer(
        "👋 <b>Вітаємо в AutoRadar!</b>\n\n"
        "Я допоможу знаходити авто на AUTO.RIA, OLX і в Telegram-групах "
        "швидше за конкурентів.\n\n"
        "Як вас звати?",
    )


@router.message(Registration.name)
async def process_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Введіть ім'я (мінімум 2 символи):")
        return

    await state.update_data(name=name)
    await state.set_state(Registration.email)
    await message.answer(
        f"Приємно познайомитись, <b>{name}</b>! 👋\n\n"
        "Тепер вкажіть email — він потрібен для входу в кабінет на сайті:",
    )


@router.message(Registration.email)
async def process_email(message: Message, state: FSMContext) -> None:
    email = (message.text or "").strip().lower()
    if not EMAIL_RE.match(email):
        await message.answer("Введіть коректний email:")
        return

    data = await state.get_data()
    name = data["name"]
    telegram_id = data["telegram_id"]
    username = data.get("username")

    token = await tg_tokens.create_registration_token(
        telegram_id=telegram_id,
        chat_id=str(message.chat.id),
        name=name,
        email=email,
        username=username,
    )
    await state.clear()

    reg_url = f"{settings.FRONTEND_URL}/auth/telegram?token={token}"
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🚀 Завершити реєстрацію", url=reg_url)]],
    )
    await message.answer(
        f"✅ <b>Майже готово!</b>\n\n"
        f"Email: <code>{email}</code>\n\n"
        "Натисніть кнопку нижче, щоб відкрити кабінет і встановити пароль.\n"
        "Після цього ви одразу отримуватимете нові авто сюди в Telegram.",
        reply_markup=markup,
    )


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Натисніть /start щоб почати роботу з AutoRadar.")


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
        await message.answer(
            "👋 Акаунт з цим Telegram не знайдено.\n\n"
            "Натисніть /start щоб зареєструватись або увійдіть через email на сайті.",
        )
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
        "Натисніть кнопку нижче, щоб увійти в AutoRadar.",
        reply_markup=markup,
    )
