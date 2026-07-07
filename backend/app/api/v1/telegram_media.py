from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter(prefix="/telegram-media", tags=["telegram-media"])


@router.get("/{path:path}")
async def get_telegram_media(path: str):
    media_root = Path(settings.TELEGRAM_MEDIA_DIR).resolve()
    file_path = (media_root / path).resolve()
    if not str(file_path).startswith(str(media_root)):
        raise HTTPException(status_code=404, detail="Not found")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(file_path)
