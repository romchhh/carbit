"""Стиснення JPEG для Telegram-медіа."""

from __future__ import annotations

import logging
import os

log = logging.getLogger("carbit_parser.media")


def compress_jpeg(
    path: str,
    *,
    max_width: int = 1280,
    quality: int = 82,
    min_bytes_to_compress: int = 80_000,
) -> bool:
    """Зменшує розмір JPEG на диску. Повертає True, якщо файл оновлено."""
    try:
        size_before = os.path.getsize(path)
    except OSError:
        return False

    if size_before <= 0:
        return False
    if size_before < min_bytes_to_compress and max_width >= 2000:
        return False

    try:
        from PIL import Image
    except ImportError:
        log.debug("Pillow not installed — skip compress for %s", path)
        return False

    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            width, height = img.size
            if width > max_width:
                height = max(1, int(height * max_width / width))
                img = img.resize((max_width, height), Image.Resampling.LANCZOS)
            tmp = f"{path}.tmp"
            img.save(tmp, "JPEG", quality=quality, optimize=True)
        os.replace(tmp, path)
        size_after = os.path.getsize(path)
        if size_after < size_before:
            log.debug(
                "Compressed %s: %s KB → %s KB",
                path,
                size_before // 1024,
                size_after // 1024,
            )
        return True
    except Exception as exc:
        log.warning("JPEG compress failed for %s: %s", path, exc)
        tmp = f"{path}.tmp"
        if os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        return False
