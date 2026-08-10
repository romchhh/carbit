from __future__ import annotations


def telegram_channel_media_slug(channel: str) -> str:
    """Єдиний slug для media/{slug}/ та listing_id."""
    return channel.strip("@").replace("/", "_").replace(" ", "_")
