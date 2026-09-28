from __future__ import annotations

import html
import logging
from pathlib import Path

from app.core.config import monitor_admin_chat_ids
from app.services.backup.split import split_file
from app.services.telegram.client import telegram_client

logger = logging.getLogger(__name__)


async def send_backup_files_to_admins(
    files: list[Path],
    *,
    label: str,
    max_part_bytes: int,
) -> list[str]:
    """Надсилає файли адмінам; великі — частинами. Повертає список помилок."""
    chat_ids = monitor_admin_chat_ids()
    if not chat_ids:
        return ["MONITOR_ADMIN_IDS не налаштовано"]
    if not telegram_client.enabled:
        return ["TELEGRAM_BOT_TOKEN не налаштовано"]

    errors: list[str] = []
    for file_path in files:
        parts = split_file(file_path, max_bytes=max_part_bytes)
        multi = len(parts) > 1
        for idx, part in enumerate(parts, start=1):
            part_label = (
                f"{label} · {file_path.name} ({idx}/{len(parts)})"
                if multi
                else f"{label} · {file_path.name}"
            )
            caption = (
                f"💾 <b>Резервна копія Carbit</b>\n"
                f"{html.escape(part_label)}\n"
                f"📦 {part.stat().st_size / (1024 * 1024):.2f} MB"
            )
            if multi:
                caption += (
                    f"\n\n<i>Частина {idx} з {len(parts)} — для відновлення "
                    f"склейте частини у правильному порядку.</i>"
                )

            for chat_id in chat_ids:
                ok = await telegram_client.send_document(
                    chat_id,
                    part,
                    caption=caption,
                    filename=part.name,
                )
                if not ok:
                    errors.append(f"Не вдалось надіслати {part.name} → {chat_id}")

        for part in parts:
            if part != file_path:
                try:
                    part.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Failed to remove temp backup part %s", part)

    return errors
