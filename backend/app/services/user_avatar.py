import logging

from app.models.models import User
from app.services.telegram.client import telegram_client

logger = logging.getLogger(__name__)


async def sync_telegram_avatar(user: User) -> None:
    if not user.telegram_id:
        user.telegram_avatar_path = None
        return
    try:
        path = await telegram_client.get_user_profile_photo_path(user.telegram_id)
        user.telegram_avatar_path = path or ""
    except Exception:
        logger.exception("Failed to sync Telegram avatar for user %s", user.id)
        user.telegram_avatar_path = ""


def user_avatar_api_path(user: User) -> str | None:
    if user.telegram_connected and user.telegram_avatar_path:
        return "/auth/me/avatar"
    return None
