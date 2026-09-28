from __future__ import annotations

import asyncio
import html
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import ROOT_DIR, settings
from app.core.timezone import now_kyiv
from app.services.backup.dump import dump_primary_database_gz, gzip_plain_file
from app.services.backup.telegram_delivery import send_backup_files_to_admins
from app.services.monitoring.alerts import notify_monitor_admins

logger = logging.getLogger(__name__)


@dataclass
class BackupRunResult:
    ok: bool
    timestamp: str
    files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    source: str = ""
    duration_seconds: float = 0.0


def _backup_dir() -> Path:
    return Path(settings.DB_BACKUP_DIR)


def _max_telegram_part_bytes() -> int:
    mb = max(1, int(settings.DB_BACKUP_TELEGRAM_MAX_MB))
    return mb * 1024 * 1024


def _prune_old_backups() -> None:
    retention = max(1, int(settings.DB_BACKUP_RETENTION_DAYS))
    cutoff = time.time() - retention * 86400
    directory = _backup_dir()
    for path in directory.glob("carbit_*"):
        if not path.is_file():
            continue
        if path.stat().st_mtime < cutoff:
            try:
                path.unlink()
                logger.info("Removed old backup %s", path.name)
            except OSError:
                logger.warning("Failed to remove old backup %s", path)


def _create_backup_files_sync(timestamp: str) -> tuple[list[Path], str]:
    directory = _backup_dir()
    main = directory / f"carbit_{timestamp}.sql.gz"
    source = dump_primary_database_gz(main)
    files: list[Path] = [main]

    if settings.DB_BACKUP_INCLUDE_KV:
        kv = ROOT_DIR / "database" / "kv.db"
        if kv.is_file() and kv.stat().st_size > 0:
            kv_gz = directory / f"carbit_kv_{timestamp}.db.gz"
            gzip_plain_file(kv, kv_gz)
            files.append(kv_gz)

    return files, source


async def run_backup_and_notify(*, manual: bool = False) -> BackupRunResult:
    started = time.monotonic()
    ts = now_kyiv().strftime("%Y%m%d_%H%M%S")
    label = "ручний" if manual else "щоденний"

    try:
        files, source = await asyncio.to_thread(_create_backup_files_sync, ts)
    except Exception as exc:
        logger.exception("Database backup failed")
        msg = f"🔴 <b>Бекап БД не вдався</b> ({html.escape(label)})\n<code>{html.escape(str(exc)[:500])}</code>"
        await notify_monitor_admins(msg)
        return BackupRunResult(
            ok=False,
            timestamp=ts,
            errors=[str(exc)],
            duration_seconds=time.monotonic() - started,
        )

    file_names = [p.name for p in files]
    sizes_mb = sum(p.stat().st_size for p in files) / (1024 * 1024)
    logger.info("Backup created: %s (%.2f MB, %s)", file_names, sizes_mb, source)

    tg_errors = await send_backup_files_to_admins(
        files,
        label=label,
        max_part_bytes=_max_telegram_part_bytes(),
    )

    await asyncio.to_thread(_prune_old_backups)

    duration = time.monotonic() - started
    if tg_errors:
        detail = "\n".join(html.escape(e) for e in tg_errors[:5])
        await notify_monitor_admins(
            f"⚠️ <b>Бекап створено</b>, але Telegram: помилки\n"
            f"Файли: <code>{html.escape(', '.join(file_names))}</code>\n{detail}"
        )
        return BackupRunResult(
            ok=False,
            timestamp=ts,
            files=file_names,
            errors=tg_errors,
            source=source,
            duration_seconds=duration,
        )

    if manual:
        await notify_monitor_admins(
            f"✅ <b>Бекап БД</b> ({html.escape(label)})\n"
            f"📁 <code>{html.escape(', '.join(file_names))}</code>\n"
            f"💾 {sizes_mb:.2f} MB · {html.escape(source)}"
        )

    return BackupRunResult(
        ok=True,
        timestamp=ts,
        files=file_names,
        source=source,
        duration_seconds=duration,
    )
