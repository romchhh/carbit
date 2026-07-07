"""Публічні посилання на повідомлення Telegram-каналів."""


def is_numeric_channel_id(value: str) -> bool:
    slug = (value or "").strip().lstrip("@")
    return bool(slug) and slug.lstrip("-").isdigit()


def public_telegram_message_url(channel_slug: str, message_id: int) -> str:
    slug = channel_slug.strip().lstrip("@")
    return f"https://t.me/{slug}/{message_id}"
