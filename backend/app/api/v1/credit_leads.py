"""Заявки на кредит (калькулятор БІЗБАНК) — сповіщення адмінам у Telegram."""

from __future__ import annotations

import html
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.services.monitoring.alerts import notify_monitor_admins

router = APIRouter(prefix="/credit-leads", tags=["credit-leads"])

_PHONE_RE = re.compile(r"^380\d{9}$")


class CreditLeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=12, max_length=13)
    listing_id: str | None = Field(default=None, max_length=128)
    listing_title: str = Field(min_length=1, max_length=500)
    listing_url: str | None = Field(default=None, max_length=2048)
    car_price_uah: int = Field(ge=0, le=50_000_000)
    down_payment_percent: float = Field(ge=0, le=100)
    term_months: int = Field(ge=1, le=120)
    loan_amount_uah: int = Field(ge=0, le=10_000_000)
    monthly_payment_uah: int = Field(ge=0, le=1_000_000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if digits.startswith("380"):
            normalized = digits[:12]
        elif digits.startswith("80") and len(digits) >= 11:
            normalized = f"3{digits}"[:12]
        elif digits.startswith("0"):
            normalized = f"38{digits}"[:12]
        else:
            normalized = f"380{digits}"[:12]
        if not _PHONE_RE.match(normalized):
            raise ValueError("invalid phone")
        return normalized


class CreditLeadResponse(BaseModel):
    ok: bool = True
    message: str = "Заявку надіслано. Ми зв'яжемося з вами найближчим часом."


@router.post("", response_model=CreditLeadResponse, status_code=201)
async def create_credit_lead(body: CreditLeadCreate) -> CreditLeadResponse:
    phone_display = f"+{body.phone[:3]} {body.phone[3:5]} {body.phone[5:8]} {body.phone[8:10]} {body.phone[10:12]}"

    lines = [
        "🏦 <b>Заявка на кредит (БІЗБАНК)</b>",
        "",
        f"👤 {html.escape(body.name)}",
        f"📞 {html.escape(phone_display)}",
        "",
        f"🚗 {html.escape(body.listing_title)}",
    ]
    if body.listing_id:
        lines.append(f"ID: <code>{html.escape(body.listing_id)}</code>")
    if body.listing_url:
        lines.append(f"🔗 {html.escape(body.listing_url)}")
    lines.extend(
        [
            "",
            f"Ціна авто: {body.car_price_uah:,} грн".replace(",", " "),
            f"Перший внесок: {body.down_payment_percent:.1f}%",
            f"Строк: {body.term_months} міс.",
            f"Сума кредиту: {body.loan_amount_uah:,} грн".replace(",", " "),
            f"Платіж: {body.monthly_payment_uah:,} грн/міс.".replace(",", " "),
        ]
    )

    try:
        await notify_monitor_admins("\n".join(lines))
    except Exception as exc:
        raise HTTPException(503, "Не вдалося надіслати заявку. Спробуйте пізніше.") from exc

    return CreditLeadResponse()
