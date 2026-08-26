"""Публічний збір відвідувань (beacon з фронтенду)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.services.admin.visit_stats import normalize_path, record_visit, resolve_visit_country
from app.services.rate_limit import client_ip, enforce_rate_limit

router = APIRouter(prefix="/analytics", tags=["analytics"])


class VisitCollectBody(BaseModel):
    path: str = Field(default="/", max_length=200)
    visitor_id: str = Field(..., min_length=8, max_length=64)
    referrer: str | None = Field(default=None, max_length=300)
    device: str | None = Field(default=None, max_length=16)


@router.post("/collect")
async def collect_visit(request: Request, body: VisitCollectBody):
    await enforce_rate_limit(
        key=f"visit:{client_ip(request)}",
        limit=180,
        window_seconds=60,
        detail="Занадто багато запитів.",
    )
    user_agent = request.headers.get("user-agent")
    country = await resolve_visit_country(request)
    await record_visit(
        path=normalize_path(body.path),
        visitor_id=body.visitor_id,
        country=country,
        user_agent=user_agent,
        device=body.device,
    )
    return {"ok": True}
