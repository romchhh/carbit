import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from config import settings  # noqa: E402
from handlers import router  # noqa: E402
from secrets_guard import assert_bot_secrets  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    assert_bot_secrets(
        debug=str(__import__("os").environ.get("DEBUG", "")).lower() in {"1", "true", "yes"}
        or "localhost" in (settings.FRONTEND_URL or "").lower(),
        internal_api_secret=settings.INTERNAL_API_SECRET,
    )
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return

    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    async def heartbeat_loop() -> None:
        from app.services.health import beat  # noqa: E402

        while True:
            try:
                await beat("bot")
            except Exception:
                logger.exception("Bot heartbeat failed")
            await asyncio.sleep(60)

    asyncio.create_task(heartbeat_loop())

    logger.info("Carbit bot started (@%s)", settings.TELEGRAM_BOT_USERNAME)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
