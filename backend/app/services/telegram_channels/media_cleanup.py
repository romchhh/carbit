"""Очищення файлів Telegram-медіа на диску."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from app.core.config import settings
from app.services.telegram_channels.freshness import listing_max_age_days

logger = logging.getLogger(__name__)

# Понад цю частку "сиріт" — ознака збою, а не реального сміття.
ORPHAN_SWEEP_MAX_SHARE = 0.8


def listing_id_to_media_path(listing_id: str) -> Path | None:
    body = listing_id.removeprefix("telegram_")
    channel_part, _, msg_part = body.rpartition("_")
    if not channel_part or not msg_part.isdigit():
        return None
    return Path(settings.TELEGRAM_MEDIA_DIR) / channel_part / f"{msg_part}.jpg"


def _album_media_paths(listing_ids: list[str]) -> list[Path]:
    """Фото альбому лежать під іншими message_id — беремо їх з refs."""
    from app.services.telegram_channels.channel_paths import telegram_channel_media_slug

    try:
        from app.services.telegram_channels.bootstrap import ensure_parser_path

        ensure_parser_path()
        from parser.channel_media_store import ChannelMediaStore
    except Exception:
        return []

    paths: list[Path] = []
    try:
        refs = ChannelMediaStore().all_photo_message_ids(listing_ids)
    except Exception:
        logger.debug("Photo refs lookup failed", exc_info=True)
        return []
    root = Path(settings.TELEGRAM_MEDIA_DIR)
    for channel, message_ids in refs.values():
        channel_dir = root / telegram_channel_media_slug(channel)
        paths.extend(channel_dir / f"{int(msg_id)}.jpg" for msg_id in message_ids)
    return paths


def delete_orphan_photo_refs(live_listing_ids: set[str]) -> int:
    """Прибирає фото й refs повідомлень, які так і не стали оголошенням.

    Такі пости відсіює ingest (не авто, дубль, застаріле), а refs і .jpg
    лишались назавжди.
    """
    if not live_listing_ids:
        # Порожня вибірка = збій БД, а не "всі оголошення зникли".
        return 0

    from app.services.telegram_channels.channel_paths import telegram_channel_media_slug

    try:
        from app.services.telegram_channels.bootstrap import ensure_parser_path

        ensure_parser_path()
        from parser.channel_media_store import ChannelMediaStore

        store = ChannelMediaStore()
        total_refs = store.photo_refs_count()
        orphans = store.orphan_photo_refs(live_listing_ids)
    except Exception:
        logger.debug("Orphan photo refs lookup failed", exc_info=True)
        return 0
    if not orphans:
        return 0

    # Якщо "сиротами" виявилась майже вся база — це збій вибірки живих
    # оголошень, а не реальні сироти. Краще нічого не чіпати.
    if len(orphans) > total_refs * ORPHAN_SWEEP_MAX_SHARE:
        logger.warning(
            "Skipped orphan photo sweep: %s of %s refs look orphaned",
            len(orphans),
            total_refs,
        )
        return 0

    root = Path(settings.TELEGRAM_MEDIA_DIR)
    removed_files = 0
    for channel, message_ids in orphans.values():
        channel_dir = root / telegram_channel_media_slug(channel)
        for msg_id in message_ids:
            path = channel_dir / f"{int(msg_id)}.jpg"
            try:
                if path.is_file():
                    path.unlink()
                    removed_files += 1
            except OSError as exc:
                logger.warning("Failed to delete orphan media %s: %s", path, exc)

    store.delete_photo_refs(list(orphans))
    logger.info(
        "Cleaned %s orphan photo ref(s), removed %s file(s)",
        len(orphans),
        removed_files,
    )
    return len(orphans)


def _drop_photo_refs(listing_ids: list[str]) -> None:
    try:
        from app.services.telegram_channels.bootstrap import ensure_parser_path

        ensure_parser_path()
        from parser.channel_media_store import ChannelMediaStore

        ChannelMediaStore().delete_photo_refs(listing_ids)
    except Exception:
        logger.debug("Photo refs cleanup failed", exc_info=True)


def delete_media_for_listing_ids(listing_ids: list[str]) -> int:
    targets: list[Path] = []
    for listing_id in listing_ids:
        path = listing_id_to_media_path(listing_id)
        if path:
            targets.append(path)
    targets.extend(_album_media_paths(listing_ids))

    removed = 0
    for path in dict.fromkeys(targets):
        try:
            if path.is_file():
                path.unlink()
                removed += 1
        except OSError as exc:
            logger.warning("Failed to delete media %s: %s", path, exc)

    _drop_photo_refs(listing_ids)
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

    age_days = max_age_days if max_age_days is not None else listing_max_age_days()
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
