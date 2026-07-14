import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend_api import (
    cancel_subscription,
    get_subscription_status,
    init_telegram_login,
    init_telegram_register,
    link_telegram_account,
)
from config import settings

logger = logging.getLogger(__name__)
router = Router()


def _user_meta(message: Message) -> tuple[str, str | None]:
    user = message.from_user
    if not user:
        raise ValueError("Missing sender")
    return str(user.id), user.username


def _format_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return iso[:10]
    except Exception:
        return iso


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


@router.message(Command("subscription", "status", "pidpiska"))
async def cmd_subscription(message: Message) -> None:
    telegram_id, _ = _user_meta(message)
    result = await get_subscription_status(telegram_id)
    if not result:
        await message.answer("⚠️ Не вдалося отримати статус. Спробуйте пізніше.")
        return
    if result.get("error") == "not_registered":
        await message.answer(
            "Акаунт не прив’язаний. Натисніть /start або підключіть Telegram у кабінеті.",
        )
        return
    if result.get("error") == "account_deactivated":
        await message.answer("⚠️ Акаунт деактивовано.")
        return

    plan_name = result.get("plan_name", "—")
    expires = _format_date(result.get("plan_expires_at"))
    if result.get("recurring_active"):
        recurring = "так"
    elif result.get("past_due"):
        recurring = "борг (оплата не пройшла)"
    else:
        recurring = "ні"
    trial = "\n🎁 Trial активний" if result.get("is_trial_active") else ""
    failed = int(result.get("failed_charges") or 0)
    failed_line = f"\n⚠️ Невдалих списань підряд: <b>{failed}</b>" if failed else ""
    billing_url = result.get("billing_url") or f"{settings.FRONTEND_URL}/app/billing"

    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💳 Керувати підпискою", url=billing_url)]],
    )
    await message.answer(
        f"📋 <b>Підписка Carbit</b>\n\n"
        f"Тариф: <b>{plan_name}</b>\n"
        f"Ліміт моніторингів: <b>{result.get('searches_limit', '—')}</b>\n"
        f"Діє до: <b>{expires}</b>\n"
        f"Автоплатіж: <b>{recurring}</b>"
        f"{trial}{failed_line}\n\n"
        f"Скасувати автоплатіж: /cancel",
        reply_markup=markup,
    )


@router.message(Command("cancel", "unsubscribe", "skasuvaty"))
async def cmd_cancel(message: Message) -> None:
    telegram_id, _ = _user_meta(message)
    result = await cancel_subscription(telegram_id)
    if not result:
        await message.answer("⚠️ Не вдалося скасувати. Спробуйте пізніше або через кабінет.")
        return
    if result.get("error") == "not_registered":
        await message.answer("Акаунт не прив’язаний. Натисніть /start.")
        return
    if result.get("error") == "account_deactivated":
        await message.answer("⚠️ Акаунт деактивовано.")
        return

    billing_url = result.get("billing_url") or f"{settings.FRONTEND_URL}/app/billing"
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Відкрити кабінет", url=billing_url)]],
    )
    text = result.get("message") or "Готово."
    expires = _format_date(result.get("plan_expires_at"))
    if result.get("already_free"):
        await message.answer(f"ℹ️ {text}", reply_markup=markup)
        return
    extra = f"\nПлатний доступ до: <b>{expires}</b>" if result.get("plan_expires_at") else ""
    await message.answer(f"✅ {text}{extra}", reply_markup=markup)


@router.message()
async def fallback(message: Message) -> None:
    await message.answer(
        "Команди Carbit:\n"
        "/start — увійти / зареєструватись\n"
        "/subscription — статус підписки\n"
        "/cancel — скасувати автоплатіж",
    )


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
        f"Команди: /subscription · /cancel\n"
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
        "Натисніть кнопку нижче, щоб увійти в Carbit.\n"
        "Підписка: /subscription · скасувати: /cancel",
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
            "У вас уже є акаунт. Натисніть кнопку, щоб увійти в кабінет.\n"
            "Підписка: /subscription · скасувати: /cancel",
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
