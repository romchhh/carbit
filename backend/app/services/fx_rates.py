"""Живі курси валют (НБУ) з кешем у KV; fallback на фіксовані значення."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# Fallback, якщо НБУ недоступний
FALLBACK_USD_TO_UAH = 45.0
FALLBACK_EUR_TO_UAH = 44.0

RATES_CACHE_KEY = "fx:nbu:uah"
RATES_TTL_SECONDS = 3600
NBU_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"


async def fetch_nbu_rates() -> dict[str, float]:
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(NBU_URL)
        response.raise_for_status()
        rows = response.json()
    usd = FALLBACK_USD_TO_UAH
    eur = FALLBACK_EUR_TO_UAH
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("cc") or "").upper()
            rate = row.get("rate")
            try:
                value = float(rate)
            except (TypeError, ValueError):
                continue
            if code == "USD" and value > 0:
                usd = value
            elif code == "EUR" and value > 0:
                eur = value
    return {"USD": usd, "EUR": eur, "UAH": 1.0}


async def get_fx_rates() -> dict[str, float]:
    try:
        redis = await get_redis()
        raw = await redis.get(RATES_CACHE_KEY)
        if raw:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("USD") and data.get("EUR"):
                return {
                    "USD": float(data["USD"]),
                    "EUR": float(data["EUR"]),
                    "UAH": 1.0,
                }
    except Exception:
        logger.debug("FX cache miss/error", exc_info=True)

    try:
        rates = await fetch_nbu_rates()
        try:
            redis = await get_redis()
            await redis.setex(RATES_CACHE_KEY, RATES_TTL_SECONDS, json.dumps(rates))
        except Exception:
            logger.debug("FX cache write failed", exc_info=True)
        return rates
    except Exception:
        logger.warning("NBU FX fetch failed — using fallback rates", exc_info=True)
        return {
            "USD": FALLBACK_USD_TO_UAH,
            "EUR": FALLBACK_EUR_TO_UAH,
            "UAH": 1.0,
        }


def sync_fallback_rates() -> dict[str, float]:
    return {
        "USD": FALLBACK_USD_TO_UAH,
        "EUR": FALLBACK_EUR_TO_UAH,
        "UAH": 1.0,
    }


# Процесний кеш для синхронних to_uah / from_uah (оновлюється async get_fx_rates)
_process_rates: dict[str, float] = sync_fallback_rates()


async def refresh_process_rates() -> dict[str, float]:
    global _process_rates
    _process_rates = await get_fx_rates()
    return _process_rates


def current_rates() -> dict[str, float]:
    return dict(_process_rates)


def usd_to_uah_rate() -> float:
    return float(_process_rates.get("USD") or FALLBACK_USD_TO_UAH)


def eur_to_uah_rate() -> float:
    return float(_process_rates.get("EUR") or FALLBACK_EUR_TO_UAH)
