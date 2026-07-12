"""Публічні курси валют для фронту."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.fx_rates import refresh_process_rates

router = APIRouter(prefix="/fx", tags=["fx"])


@router.get("/rates")
async def fx_rates():
    rates = await refresh_process_rates()
    return {
        "USD": rates.get("USD"),
        "EUR": rates.get("EUR"),
        "UAH": 1.0,
        "source": "nbu",
    }
