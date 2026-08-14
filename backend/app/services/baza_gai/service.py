from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.core.config import settings
from app.core.redis import get_redis
from app.schemas.schemas import (
    VinAuctionOut,
    VinCheckOperationOut,
    VinCheckOut,
    VinCheckRegionOut,
    VinCheckStolenOut,
)
from app.services.autohelperbot.service import lookup_vin_auction
from app.services.baza_gai.client import BazaGaiClient
from app.services.baza_gai.errors import BazaGaiError, BazaGaiNotFound
from app.services.vin import is_valid_vin

logger = logging.getLogger(__name__)

CACHE_HIT_TTL = 60 * 60 * 24 * 7  # 7 днів
CACHE_MISS_TTL = 60 * 60 * 24  # 1 день
CACHE_PREFIX = "vin:baza:"
MISSING_MARKER = {"_missing": True}


def normalize_vin(value: str | None) -> str | None:
    if not value:
        return None
    vin = "".join(ch for ch in value.strip().upper() if ch.isalnum())
    return vin if is_valid_vin(vin) else None


def _locale_text(obj: Any, *, prefer_ua: bool = True) -> str | None:
    if obj is None:
        return None
    if isinstance(obj, str):
        text = obj.strip()
        return text or None
    if isinstance(obj, dict):
        if prefer_ua:
            for key in ("ua", "uk", "title_uk", "title_ua"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        for key in ("ru", "title_ru", "title", "name"):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        nested = obj.get("title")
        if isinstance(nested, dict):
            return _locale_text(nested, prefer_ua=prefer_ua)
    return None


def map_baza_gai_vin_payload(raw: dict[str, Any], *, vin: str) -> VinCheckOut:
    region_raw = raw.get("region") if isinstance(raw.get("region"), dict) else {}
    region = None
    if region_raw:
        codes: list[str] = []
        for c in (region_raw.get("old_code"), region_raw.get("new_code")):
            if isinstance(c, str) and c.strip():
                codes.append(c.strip())
        extra_codes = region_raw.get("codes")
        if isinstance(extra_codes, list):
            for c in extra_codes:
                if isinstance(c, str) and c.strip():
                    codes.append(c.strip())
        seen_codes: set[str] = set()
        codes = [c for c in codes if not (c in seen_codes or seen_codes.add(c))]

        name_ua = (
            region_raw["name_ua"].strip()
            if isinstance(region_raw.get("name_ua"), str) and region_raw["name_ua"].strip()
            else None
        )
        region = VinCheckRegionOut(
            name=_locale_text(region_raw.get("name")),
            name_ua=name_ua or _locale_text(region_raw.get("name")),
            slug=region_raw.get("slug") if isinstance(region_raw.get("slug"), str) else None,
            codes=codes,
        )

    operations: list[VinCheckOperationOut] = []
    for item in raw.get("operations") or []:
        if not isinstance(item, dict):
            continue
        color = item.get("color") if isinstance(item.get("color"), dict) else {}
        operation = item.get("operation") if isinstance(item.get("operation"), dict) else {}
        operation_group = (
            item.get("operation_group") if isinstance(item.get("operation_group"), dict) else {}
        )
        kind = item.get("kind") if isinstance(item.get("kind"), dict) else {}
        operations.append(
            VinCheckOperationOut(
                registered_at=item.get("registered_at") if isinstance(item.get("registered_at"), str) else None,
                is_last=bool(item.get("is_last")) if item.get("is_last") is not None else None,
                digits=item.get("digits") if isinstance(item.get("digits"), str) else None,
                vendor=item.get("vendor") if isinstance(item.get("vendor"), str) else None,
                model=item.get("model") if isinstance(item.get("model"), str) else None,
                model_year=item.get("model_year") if isinstance(item.get("model_year"), int) else None,
                operation_ua=_locale_text(operation, prefer_ua=True),
                operation_ru=_locale_text(operation, prefer_ua=False),
                operation_group_ua=_locale_text(operation_group, prefer_ua=True),
                department=item.get("department") if isinstance(item.get("department"), str) else None,
                color=_locale_text(color),
                displacement=item.get("displacement")
                if isinstance(item.get("displacement"), (int, float))
                else None,
                address=item.get("address") if isinstance(item.get("address"), str) else None,
                kind_ua=_locale_text(kind, prefer_ua=True),
                is_registered_to_company=bool(item.get("is_registered_to_company"))
                if item.get("is_registered_to_company") is not None
                else None,
            )
        )

    stolen: list[VinCheckStolenOut] = []
    for item in raw.get("stolen_details") or []:
        if not isinstance(item, dict):
            continue
        color = item.get("color") if isinstance(item.get("color"), dict) else {}
        stolen.append(
            VinCheckStolenOut(
                theft_at=item.get("theft_at") if isinstance(item.get("theft_at"), str) else None,
                vendor_title=item.get("vendor_title")
                if isinstance(item.get("vendor_title"), str)
                else None,
                color=_locale_text(color) or (
                    item.get("raw_color") if isinstance(item.get("raw_color"), str) else None
                ),
                car_type=item.get("car_type") if isinstance(item.get("car_type"), str) else None,
                chassis_number=item.get("chassis_number")
                if isinstance(item.get("chassis_number"), str)
                else None,
                body_number=item.get("body_number")
                if isinstance(item.get("body_number"), str)
                else None,
                department_title=item.get("department_title")
                if isinstance(item.get("department_title"), str)
                else None,
            )
        )

    resolved_vin = raw.get("vin") if isinstance(raw.get("vin"), str) and raw.get("vin") else vin
    plate = raw.get("digits") if isinstance(raw.get("digits"), str) else None
    if not plate:
        for op in operations:
            if op.is_last and op.digits:
                plate = op.digits
                break
        if not plate:
            for op in operations:
                if op.digits:
                    plate = op.digits
                    break

    latest = next((op for op in operations if op.is_last), operations[0] if operations else None)
    dated_ops = [op for op in operations if op.registered_at]
    # База ДАІ віддає історії від новіших до старших
    first_registered_at = dated_ops[-1].registered_at if dated_ops else None
    last_registered_at = dated_ops[0].registered_at if dated_ops else None
    base = (settings.BAZA_GAI_BASE_URL or "https://baza-gai.com.ua").rstrip("/")

    return VinCheckOut(
        vin=resolved_vin.upper(),
        plate=plate,
        vendor=raw.get("vendor") if isinstance(raw.get("vendor"), str) else None,
        model=raw.get("model") if isinstance(raw.get("model"), str) else None,
        model_year=raw.get("model_year") if isinstance(raw.get("model_year"), int) else None,
        photo_url=raw.get("photo_url") if isinstance(raw.get("photo_url"), str) else None,
        is_stolen=bool(raw.get("is_stolen")) if raw.get("is_stolen") is not None else False,
        color=latest.color if latest else None,
        displacement=latest.displacement if latest else None,
        kind_ua=latest.kind_ua if latest else None,
        registrations_count=len(operations),
        first_registered_at=first_registered_at,
        last_registered_at=last_registered_at,
        region=region,
        operations=operations,
        stolen_details=stolen,
        source_url=f"{base}/vin/{resolved_vin.upper()}",
        note="Дані Бази ДАІ здебільшого доступні для реєстрацій з 2021 року.",
    )


def _cache_key(vin: str) -> str:
    return f"{CACHE_PREFIX}{vin}"


def _vin_check_from_auction(vin: str, auction: VinAuctionOut) -> VinCheckOut:
    title = (auction.title or "").strip().replace("\n", " ")
    # Прибрати VIN з кінця title, якщо приліпився.
    if vin and title.upper().endswith(vin.upper()):
        title = title[: -len(vin)].strip(" -|/")
    vendor = None
    model = None
    model_year = None
    if title:
        bits = [b for b in title.split() if b]
        if bits and bits[0].isdigit() and len(bits[0]) == 4:
            try:
                model_year = int(bits[0])
            except ValueError:
                model_year = None
            bits = bits[1:]
        if bits:
            vendor = bits[0]
            model = " ".join(bits[1:]) or None

    note_parts = [
        "У Базі ДАІ VIN не знайдено.",
        "Показано аукціонну історію (autohelperbot).",
    ]
    return VinCheckOut(
        vin=vin,
        vendor=vendor,
        model=model,
        model_year=model_year,
        photo_url=auction.photo_url,
        color=auction.color,
        is_stolen=False,
        registrations_count=0,
        operations=[],
        stolen_details=[],
        source_url=auction.page_url or f"https://autohelperbot.com/car/{vin}",
        note=" ".join(note_parts),
        auction=auction,
    )


async def _lookup_baza_only(vin: str) -> VinCheckOut:
    try:
        redis = await get_redis()
        cached = await redis.get(_cache_key(vin))
        if cached:
            data = json.loads(cached)
            if isinstance(data, dict):
                if data.get("_missing"):
                    raise BazaGaiNotFound(vin)
                return VinCheckOut.model_validate(data)
    except BazaGaiNotFound:
        raise
    except Exception:
        logger.exception("VIN cache read failed")

    client = BazaGaiClient()
    try:
        raw = await client.lookup_vin(vin)
    except BazaGaiNotFound:
        try:
            redis = await get_redis()
            await redis.setex(_cache_key(vin), CACHE_MISS_TTL, json.dumps(MISSING_MARKER))
        except Exception:
            logger.exception("VIN miss cache write failed")
        raise

    result = map_baza_gai_vin_payload(raw, vin=vin)
    try:
        redis = await get_redis()
        await redis.setex(
            _cache_key(vin),
            CACHE_HIT_TTL,
            result.model_dump_json(),
        )
    except Exception:
        logger.exception("VIN hit cache write failed")

    return result


async def lookup_vin_check(vin_raw: str) -> VinCheckOut:
    vin = normalize_vin(vin_raw)
    if not vin:
        raise ValueError("Невалідний VIN")

    baza_task = asyncio.create_task(_lookup_baza_only(vin))
    auction_task = (
        asyncio.create_task(lookup_vin_auction(vin))
        if settings.VIN_AUCTION_CHECK_ENABLED
        else None
    )

    baza_result: VinCheckOut | None = None
    baza_fatal: BazaGaiError | None = None
    try:
        baza_result = await baza_task
    except BazaGaiNotFound:
        pass
    except BazaGaiError as exc:
        baza_fatal = exc
        logger.exception("Baza GAI VIN lookup failed; trying auction fallback")

    auction: VinAuctionOut | None = None
    if auction_task is not None:
        try:
            auction = await asyncio.wait_for(
                auction_task,
                timeout=settings.VIN_AUCTION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("VIN auction timed out for %s", vin)
            auction_task.cancel()
        except Exception:
            logger.exception("VIN auction failed for %s", vin)

    if baza_result is not None:
        if auction is not None:
            baza_result.auction = auction
            if not baza_result.photo_url and auction.photo_url:
                baza_result.photo_url = auction.photo_url
        return baza_result

    if auction is not None:
        return _vin_check_from_auction(vin, auction)

    if baza_fatal is not None:
        raise baza_fatal
    raise BazaGaiNotFound(vin)
