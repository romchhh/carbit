"""Заявки на кредит (калькулятор БІЗБАНК) — email банку + сповіщення адмінам у Telegram."""

from __future__ import annotations

import html
import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.services.email import send_credit_lead_email
from app.services.monitoring.alerts import notify_monitor_admins

logger = logging.getLogger(__name__)

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
    monthly_payment_from_month2_uah: int | None = Field(default=None, ge=0, le=1_000_000)
    registration_mode: str | None = Field(default=None, max_length=32)
    nominal_rate_percent: float | None = Field(default=None, ge=0, le=200)
    real_annual_rate_percent: float | None = Field(default=None, ge=0, le=200)
    total_repayment_uah: int | None = Field(default=None, ge=0, le=50_000_000)
    one_time_fee_uah: int | None = Field(default=None, ge=0, le=1_000_000)
    notary_fee_uah: int | None = Field(default=None, ge=0, le=1_000_000)

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
        ]
    )
    if body.registration_mode == "without_registration":
        lines.append("Режим: без реєстрації ТЗ")
    elif body.registration_mode == "with_registration":
        lines.append("Режим: з реєстрацією ТЗ")
    if body.nominal_rate_percent is not None:
        lines.append(f"Номінальна ставка: {body.nominal_rate_percent:.2f}%")
    if body.real_annual_rate_percent is not None:
        lines.append(f"Реальна річна (XIRR): ~{body.real_annual_rate_percent:.1f}%")
    if (
        body.monthly_payment_from_month2_uah is not None
        and body.monthly_payment_from_month2_uah != body.monthly_payment_uah
    ):
        lines.append(
            f"Платіж: {body.monthly_payment_uah:,} грн (1-й міс.), "
            f"далі {body.monthly_payment_from_month2_uah:,} грн/міс.".replace(",", " ")
        )
    else:
        lines.append(f"Платіж: {body.monthly_payment_uah:,} грн/міс.".replace(",", " "))
    if body.one_time_fee_uah is not None:
        lines.append(f"Разова комісія: {body.one_time_fee_uah:,} грн".replace(",", " "))
    if body.notary_fee_uah is not None and body.notary_fee_uah > 0:
        lines.append(f"Нотаріальні: {body.notary_fee_uah:,} грн".replace(",", " "))
    if body.total_repayment_uah is not None:
        lines.append(f"Разом за строк: {body.total_repayment_uah:,} грн".replace(",", " "))

    email_to = (settings.CREDIT_LEAD_EMAIL or "").strip()
    if email_to:
        def money(n: int) -> str:
            return f"{n:,} грн".replace(",", " ")

        email_rows: list[tuple[str, str]] = [
            ("Ім'я", html.escape(body.name)),
            ("Телефон", html.escape(phone_display)),
            ("Авто", html.escape(body.listing_title)),
        ]
        if body.listing_id:
            email_rows.append(("ID оголошення", html.escape(body.listing_id)))
        if body.listing_url:
            email_rows.append(
                (
                    "Посилання",
                    f'<a href="{html.escape(body.listing_url, quote=True)}">{html.escape(body.listing_url)}</a>',
                )
            )
        email_rows.extend(
            [
                ("Ціна авто", money(body.car_price_uah)),
                ("Перший внесок", f"{body.down_payment_percent:.1f}%"),
                ("Строк", f"{body.term_months} міс."),
                ("Сума кредиту", money(body.loan_amount_uah)),
            ]
        )
        if body.registration_mode == "without_registration":
            email_rows.append(("Режим", "без реєстрації ТЗ"))
        elif body.registration_mode == "with_registration":
            email_rows.append(("Режим", "з реєстрацією ТЗ"))
        if body.nominal_rate_percent is not None:
            email_rows.append(("Номінальна ставка", f"{body.nominal_rate_percent:.2f}%"))
        if body.real_annual_rate_percent is not None:
            email_rows.append(("Реальна річна (XIRR)", f"~{body.real_annual_rate_percent:.1f}%"))
        if (
            body.monthly_payment_from_month2_uah is not None
            and body.monthly_payment_from_month2_uah != body.monthly_payment_uah
        ):
            email_rows.append(
                (
                    "Платіж",
                    f"{money(body.monthly_payment_uah)} (1-й міс.), далі {money(body.monthly_payment_from_month2_uah)}/міс.",
                )
            )
        else:
            email_rows.append(("Платіж", f"{money(body.monthly_payment_uah)}/міс."))
        if body.one_time_fee_uah is not None:
            email_rows.append(("Разова комісія", money(body.one_time_fee_uah)))
        if body.notary_fee_uah is not None and body.notary_fee_uah > 0:
            email_rows.append(("Нотаріальні", money(body.notary_fee_uah)))
        if body.total_repayment_uah is not None:
            email_rows.append(("Разом за строк", money(body.total_repayment_uah)))

        try:
            await send_credit_lead_email(
                to=email_to,
                subject=f"Заявка на кредит — {body.name} — {body.listing_title[:80]}",
                rows=email_rows,
            )
        except Exception as exc:
            raise HTTPException(503, "Не вдалося надіслати заявку. Спробуйте пізніше.") from exc
    else:
        logger.warning("CREDIT_LEAD_EMAIL is empty — credit lead email skipped")

    try:
        await notify_monitor_admins("\n".join(lines))
    except Exception:
        logger.exception("Failed to notify admins about credit lead")

    return CreditLeadResponse()
