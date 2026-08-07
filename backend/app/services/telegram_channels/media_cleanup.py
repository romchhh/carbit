"""Очищення файлів Telegram-медіа на диску."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from app.core.config import settings
from app.services.telegram_channels.freshness import TELEGRAM_LISTING_MAX_AGE_DAYS

logger = logging.getLogger(__name__)


def listing_id_to_media_path(listing_id: str) -> Path | None:
    body = listing_id.removeprefix("telegram_")
    channel_part, _, msg_part = body.rpartition("_")
    if not channel_part or not msg_part.isdigit():
        return None
    return Path(settings.TELEGRAM_MEDIA_DIR) / channel_part / f"{msg_part}.jpg"


def delete_media_for_listing_ids(listing_ids: list[str]) -> int:
    removed = 0
    for listing_id in listing_ids:
        path = listing_id_to_media_path(listing_id)
        if not path:
            continue
        try:
            if path.is_file():
                path.unlink()
                removed += 1
        except OSError as exc:
            logger.warning("Failed to delete media %s: %s", path, exc)
    if removed:
        logger.info("Deleted %s Telegram media file(s) for purged listings", removed)
    return removed


def purge_stale_media_files(
    *,
    max_age_days: int | None = None,
    dry_run: bool = False,
) -> int:
    """Видаляє .jpg старші за max_age_days за mtime (сироти та застарілі)."""
    root = Path(settings.TELEGRAM_MEDIA_DIR)
    if not root.is_dir():
        return 0

    age_days = max_age_days if max_age_days is not None else TELEGRAM_LISTING_MAX_AGE_DAYS
    cutoff = time.time() - age_days * 86400
    removed = 0

    for path in root.rglob("*.jpg"):
        try:
            if path.stat().st_mtime >= cutoff:
                continue
        except OSError:
            continue
        if dry_run:
            removed += 1
            continue
        try:
            path.unlink()
            removed += 1
        except OSError as exc:
            logger.warning("Failed to delete stale media %s: %s", path, exc)

    if removed:
        logger.info(
            "Purged %s stale Telegram media file(s) older than %s days%s",
            removed,
            age_days,
            " (dry-run)" if dry_run else "",
        )
    return removed
