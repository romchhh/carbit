import logging

from app.models.models import User
from app.services.telegram.client import telegram_client

logger = logging.getLogger(__name__)


async def sync_telegram_avatar(user: User) -> bool:
    if not user.telegram_id:
        changed = user.telegram_avatar_path is not None
        user.telegram_avatar_path = None
        return changed
    try:
        path = await telegram_client.get_user_profile_photo_path(user.telegram_id)
        new_path = path or ""
        old_path = user.telegram_avatar_path or ""
        if new_path == old_path:
            return False
        user.telegram_avatar_path = new_path or None
        return True
    except Exception:
        logger.exception("Failed to sync Telegram avatar for user %s", user.id)
        if user.telegram_avatar_path:
            user.telegram_avatar_path = None
            return True
        return False


def user_avatar_api_path(user: User) -> str | None:
    if user.telegram_connected and user.telegram_avatar_path:
        return "/auth/me/avatar"
    return None


def admin_user_avatar_api_path(user: User) -> str | None:
    if user.telegram_connected and user.telegram_avatar_path:
        return f"/admin/users/{user.id}/avatar"
    return None
