from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter(prefix="/telegram-media", tags=["telegram-media"])


@router.get("/{path:path}")
async def get_telegram_media(path: str):
    media_root = Path(settings.TELEGRAM_MEDIA_DIR).resolve()
    try:
        file_path = (media_root / path).resolve()
        file_path.relative_to(media_root)
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="Not found") from None
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(file_path)
