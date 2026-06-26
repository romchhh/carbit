import logging

import httpx

from app.core.config import settings
from app.services.email_templates import verification_code_email, welcome_email, password_reset_email

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html: str) -> None:
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s", to)
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
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
        if res.status_code >= 400:
            logger.error("Resend error %s: %s", res.status_code, res.text)
            raise RuntimeError("Failed to send email")


async def send_verification_code(to: str, name: str, code: str) -> None:
    subject, html = verification_code_email(name, code)
    await send_email(to, subject, html)


async def send_welcome_email(to: str, name: str) -> None:
    dashboard_url = f"{settings.FRONTEND_URL}/app/dashboard"
    subject, html = welcome_email(name, dashboard_url)
    await send_email(to, subject, html)


async def send_password_reset_email(to: str, name: str, reset_url: str) -> None:
    subject, html = password_reset_email(name, reset_url)
    await send_email(to, subject, html)
