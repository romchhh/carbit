import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from handlers import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    if not settings.TELEGRAM_SUPPORT_BOT_TOKEN:
        logger.error("TELEGRAM_SUPPORT_BOT_TOKEN not set — support bot stopped")
        return
    if not settings.admin_chat_id:
        logger.error("TELEGRAM_SUPPORT_ADMIN_CHAT_ID / TELEGRAM_ADMIN_CHAT_ID not set")
        return

    bot = Bot(
        token=settings.TELEGRAM_SUPPORT_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    me = await bot.get_me()
    logger.info(
        "Carbit support bot started (@%s), admin=%s",
        me.username or "?",
        settings.admin_chat_id,
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
