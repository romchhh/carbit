#!/usr/bin/env python3
"""Разове стиснення та/або видалення старих Telegram-фото на диску.

Локально:
  cd carbit
  PYTHONPATH=backend:. python backend/scripts/purge_telegram_media.py --dry-run --compress --purge-old

Docker (VPS):
  docker compose run --rm --entrypoint python backend \\
    backend/scripts/purge_telegram_media.py --dry-run --compress --purge-old
"""
from __future__ import annotations

import argparse

from app.core.config import settings
from app.services.telegram_channels.freshness import listing_max_age_days
from app.services.telegram_channels.media_cleanup import purge_stale_media_files
from parser.media_compress import compress_jpeg


def compress_all(*, dry_run: bool) -> tuple[int, int]:
    from pathlib import Path

    root = Path(settings.TELEGRAM_MEDIA_DIR)
    if not root.is_dir():
        print(f"Media dir not found: {root}")
        return 0, 0

    touched = 0
    saved_bytes = 0
    for path in root.rglob("*.jpg"):
        try:
            before = path.stat().st_size
        except OSError:
            continue
        if before < 80_000:
            continue
        if dry_run:
            touched += 1
            continue
        if compress_jpeg(str(path), max_width=1280, quality=82, min_bytes_to_compress=0):
            try:
                after = path.stat().st_size
                if after < before:
                    saved_bytes += before - after
                    touched += 1
            except OSError:
                pass
    return touched, saved_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram media disk maintenance")
    parser.add_argument("--compress", action="store_true", help="Compress large JPEG files")
    parser.add_argument(
        "--purge-old", action="store_true", help="Delete JPEG past the retention window"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=listing_max_age_days(),
        help="Age for --purge-old (default: LISTING_MAX_AGE_DAYS)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show counts only")
    args = parser.parse_args()

    if not args.compress and not args.purge_old:
        parser.print_help()
        return 1

    print(f"Media dir: {settings.TELEGRAM_MEDIA_DIR}")

    if args.compress:
        count, saved = compress_all(dry_run=args.dry_run)
        label = "Would compress" if args.dry_run else "Compressed"
        print(f"{label} {count} file(s), saved ~{saved // (1024 * 1024)} MB")

    if args.purge_old:
        removed = purge_stale_media_files(max_age_days=args.days, dry_run=args.dry_run)
        label = "Would remove" if args.dry_run else "Removed"
        print(f"{label} {removed} stale file(s) (>{args.days} days)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
