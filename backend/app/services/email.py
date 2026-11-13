import logging

import httpx

from app.core.config import settings
from app.services.email_templates import verification_code_email, welcome_email, password_reset_email

logger = logging.getLogger(__name__)


async def send_email(to: str | list[str], subject: str, html: str) -> None:
    recipients = [to] if isinstance(to, str) else list(to)
    recipients = [r.strip() for r in recipients if r and r.strip()]
    if not recipients:
        logger.warning("send_email called with empty recipients — skipping")
        return
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s", recipients)
        return

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.EMAIL_FROM,
                "to": recipients,
                "subject": subject,
                "html": html,
            },
        )
        if res.status_code >= 400:
            logger.error("Resend error %s: %s", res.status_code, res.text)
            raise RuntimeError("Failed to send email")


async def send_verification_code(to: str, name: str, code: str) -> None:
    subject, html = verification_code_email(name, code, email=to)
    await send_email(to, subject, html)


async def send_welcome_email(to: str, name: str) -> None:
    dashboard_url = f"{settings.FRONTEND_URL}/app/dashboard"
    subject, html = welcome_email(name, dashboard_url)
    await send_email(to, subject, html)


async def send_password_reset_email(to: str, name: str, reset_url: str) -> None:
    subject, html = password_reset_email(name, reset_url)
    await send_email(to, subject, html)


async def send_credit_lead_email(*, to: str | list[str], subject: str, rows: list[tuple[str, str]]) -> None:
    """Надсилає заявку на кредит на email банку/менеджера (можна кілька адрес)."""
    body_rows = "".join(
        f"<tr>"
        f'<td style="padding:6px 12px 6px 0;color:#6b7280;vertical-align:top;white-space:nowrap;">{label}</td>'
        f'<td style="padding:6px 0;color:#0a0c0e;font-weight:600;">{value}</td>'
        f"</tr>"
        for label, value in rows
    )
    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:24px;background:#f7f8fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;padding:24px;border:1px solid #e4e6ea;">
    <p style="margin:0 0 4px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#6b7280;">Carbit · БІЗБАНК</p>
    <h1 style="margin:0 0 20px;font-size:20px;color:#0a0c0e;">Заявка на кредит</h1>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">{body_rows}</table>
    <p style="margin:20px 0 0;font-size:12px;color:#9ca3af;line-height:1.4;">
      Заявку сформовано в кредитному калькуляторі на carbit.info. Це не оферта — рішення приймає банк.
    </p>
  </div>
</body></html>"""
    await send_email(to, subject, html)
