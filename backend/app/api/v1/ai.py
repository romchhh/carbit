"""AI: голосовий і текстовий розбір пошукових фільтрів."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.ai.search_parser import parse_search_text, transcribe_audio

router = APIRouter(prefix="/ai", tags=["ai"])

MAX_AUDIO_BYTES = 10 * 1024 * 1024


class ParseSearchRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


@router.post("/parse-search")
async def parse_search(body: ParseSearchRequest):
    """Розбір тексту (транскрипту) у фільтри пошуку."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(503, "Голосовий пошук тимчасово недоступний")
    return await parse_search_text(body.text)


@router.post("/transcribe-search")
async def transcribe_search(audio: UploadFile = File(...)):
    """Whisper-транскрипція + розбір фільтрів (fallback без Web Speech API)."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(503, "Голосовий пошук тимчасово недоступний")

    data = await audio.read()
    if not data:
        raise HTTPException(400, "Порожній аудіофайл")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(400, "Аудіо занадто довге (макс. 10 хв)")

    filename = audio.filename or "voice.webm"
    transcript = await transcribe_audio(data, filename=filename)
    if not transcript:
        return {
            "understood": False,
            "message": "Не зрозумів — не вдалося розпізнати мовлення.",
            "transcript": "",
            "filters": {},
        }

    result = await parse_search_text(transcript)
    result["transcript"] = transcript
    return result
