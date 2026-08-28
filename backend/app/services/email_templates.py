from __future__ import annotations

from html import escape
from urllib.parse import quote

from app.core.config import settings

_EMERALD = "#00C896"
_EMERALD_DARK = "#00A47C"
_INK = "#0A0C0E"
_MUTED = "#6B7280"
_SURFACE = "#F7F8FA"
_BORDER = "#E4E6EA"

_COPY_ICON_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
    "fill='none' viewBox='0 0 24 24'%3E%3Crect x='9' y='9' width='11' height='11' rx='2' "
    "stroke='%23ffffff' stroke-width='2'/%3E%3Cpath d='M7 15H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v1' "
    "stroke='%23ffffff' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E"
)


def _frontend_url() -> str:
    return settings.FRONTEND_URL.rstrip("/")


def _logo_url(*, light: bool = True) -> str:
    name = "logo-carbit-white.png" if light else "logo-carbit.png"
    return f"{_frontend_url()}/icons/{name}"


def _verify_code_url(email: str, code: str) -> str:
    return (
        f"{_frontend_url()}/auth/login"
        f"?tab=register&step=verify&email={quote(email)}&code={quote(code)}"
    )


def _code_block(code: str, verify_url: str) -> str:
    safe_code = escape(code)
    safe_url = escape(verify_url, quote=True)
    return f"""
      <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 20px;">
        <tr>
          <td style="background:linear-gradient(180deg,#F0FDF9 0%,#F7F8FA 100%);
                     border:1px solid rgba(0,200,150,0.22);border-radius:18px;padding:28px 20px 22px;
                     text-align:center;">
            <p style="margin:0 0 14px;font-size:11px;font-weight:700;letter-spacing:0.12em;
                      text-transform:uppercase;color:{_EMERALD_DARK};">
              Ваш код
            </p>
            <p style="margin:0 0 22px;font-size:38px;font-weight:900;letter-spacing:0.28em;
                      color:{_INK};font-family:ui-monospace,'SF Mono',Consolas,monospace;line-height:1;">
              {safe_code}
            </p>
            <table cellpadding="0" cellspacing="0" align="center">
              <tr>
                <td style="background:{_EMERALD};border-radius:999px;
                           box-shadow:0 4px 14px rgba(0,200,150,0.35);">
                  <a href="{safe_url}"
                     style="display:inline-block;padding:12px 22px;font-size:14px;font-weight:700;
                            color:#ffffff;text-decoration:none;line-height:1;">
                    <img src="{_COPY_ICON_SVG}" width="18" height="18" alt=""
                         style="vertical-align:middle;margin-right:8px;border:0;display:inline-block;"/>
                    <span style="vertical-align:middle;">Скопіювати код</span>
                  </a>
                </td>
              </tr>
            </table>
            <p style="margin:14px 0 0;font-size:12px;color:{_MUTED};line-height:1.5;">
              Або виділіть код пальцем / мишею та скопіюйте вручну
            </p>
          </td>
        </tr>
      </table>
    """


def _cta_button(label: str, href: str) -> str:
    safe_href = escape(href, quote=True)
    return f"""
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td align="center">
            <a href="{safe_href}"
               style="display:inline-block;background:{_EMERALD};color:#ffffff;font-size:14px;font-weight:700;
                      text-decoration:none;padding:14px 32px;border-radius:999px;
                      box-shadow:0 4px 14px rgba(0,200,150,0.35);">
              {escape(label)}
            </a>
          </td>
        </tr>
      </table>
    """


def _base_layout(content: str) -> str:
    logo = escape(_logo_url(light=True))
    site = escape(_frontend_url(), quote=True)
    site_label = escape(_frontend_url().replace("https://", "").replace("http://", ""))
    return f"""<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="color-scheme" content="light"/>
  <meta name="supported-color-schemes" content="light"/>
  <title>Carbit</title>
</head>
<body style="margin:0;padding:0;background:{_SURFACE};
             font-family:'Segoe UI',system-ui,-apple-system,BlinkMacSystemFont,sans-serif;
             -webkit-font-smoothing:antialiased;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_SURFACE};padding:32px 16px 40px;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="max-width:520px;background:#ffffff;border-radius:24px;border:1px solid {_BORDER};
                      overflow:hidden;box-shadow:0 8px 32px rgba(10,12,14,0.08);">
          <tr>
            <td style="background:linear-gradient(135deg,#0A0C0E 0%,#15181C 55%,#1A2420 100%);
                       padding:28px 32px 26px;">
              <a href="{site}" style="text-decoration:none;display:inline-block;">
                <img src="{logo}" alt="Carbit" width="132" height="36"
                     style="display:block;height:36px;width:auto;max-width:160px;border:0;"/>
              </a>
              <p style="margin:14px 0 0;font-size:12px;color:rgba(255,255,255,0.45);line-height:1.5;">
                Агрегатор авторинку України
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 32px 28px;">
              {content}
            </td>
          </tr>
          <tr>
            <td style="padding:22px 32px 28px;border-top:1px solid {_BORDER};background:{_SURFACE};">
              <p style="margin:0;font-size:12px;color:{_MUTED};line-height:1.7;text-align:center;">
                © 2026 Carbit · Агрегатор авторинку України<br/>
                <a href="{site}" style="color:{_EMERALD_DARK};text-decoration:none;font-weight:600;">
                  {site_label}
                </a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def verification_code_email(name: str, code: str, email: str = "") -> tuple[str, str]:
    subject = f"{code} — код підтвердження Carbit"
    safe_name = escape(name)
    verify_url = _verify_code_url(email, code) if email else _frontend_url() + "/auth/login"
    content = f"""
      <p style="margin:0 0 6px;font-size:14px;color:{_MUTED};line-height:1.5;">
        Привіт, <strong style="color:{_INK};">{safe_name}</strong>!
      </p>
      <h1 style="margin:0 0 10px;font-size:24px;font-weight:800;color:{_INK};letter-spacing:-0.03em;line-height:1.2;">
        Підтвердіть email
      </h1>
      <p style="margin:0 0 24px;font-size:15px;color:{_MUTED};line-height:1.65;">
        Введіть цей код на сторінці реєстрації. Він дійсний
        <strong style="color:{_INK};">10 хвилин</strong>.
      </p>
      {_code_block(code, verify_url)}
      <p style="margin:0;font-size:13px;color:{_MUTED};line-height:1.65;">
        Якщо ви не реєструвались в Carbit — просто проігноруйте цей лист.
      </p>
    """
    return subject, _base_layout(content)


def welcome_email(name: str, dashboard_url: str) -> tuple[str, str]:
    first_name = escape(name.split()[0] if name.strip() else name)
    subject = f"Ласкаво просимо в Carbit, {first_name}! 🚗"
    content = f"""
      <p style="margin:0 0 6px;font-size:14px;color:{_MUTED};">Вітаємо, {first_name}!</p>
      <h1 style="margin:0 0 10px;font-size:24px;font-weight:800;color:{_INK};letter-spacing:-0.03em;">
        Ваш акаунт активовано
      </h1>
      <p style="margin:0 0 24px;font-size:15px;color:{_MUTED};line-height:1.65;">
        Тепер Carbit моніторить AUTO.RIA, OLX і Telegram за вас — і сповіщає про нові авто раніше за конкурентів.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
        <tr>
          <td style="padding:16px 18px;background:{_SURFACE};border:1px solid {_BORDER};border-radius:14px;">
            <span style="font-size:20px;line-height:1;">🔍</span>
            <strong style="display:block;margin-top:8px;font-size:14px;color:{_INK};">Створіть перший пошук</strong>
            <span style="font-size:13px;color:{_MUTED};line-height:1.5;">
              Налаштуйте фільтри — ми знайдемо авто автоматично
            </span>
          </td>
        </tr>
        <tr><td style="height:10px;"></td></tr>
        <tr>
          <td style="padding:16px 18px;background:{_SURFACE};border:1px solid {_BORDER};border-radius:14px;">
            <span style="font-size:20px;line-height:1;">⚡</span>
            <strong style="display:block;margin-top:8px;font-size:14px;color:{_INK};">Отримуйте сповіщення</strong>
            <span style="font-size:13px;color:{_MUTED};line-height:1.5;">
              Нові оголошення — за лічені хвилини
            </span>
          </td>
        </tr>
      </table>
      {_cta_button("Перейти до кабінету →", dashboard_url)}
      <p style="margin:20px 0 0;font-size:12px;color:{_MUTED};text-align:center;line-height:1.6;">
        7 днів «Старт» безкоштовно · VIN без обмежень · Без прив&apos;язки карти
      </p>
    """
    return subject, _base_layout(content)


def password_reset_email(name: str, reset_url: str) -> tuple[str, str]:
    first_name = escape(name.split()[0] if name.strip() else name)
    subject = "Скидання пароля Carbit"
    content = f"""
      <p style="margin:0 0 6px;font-size:14px;color:{_MUTED};">Привіт, {first_name}!</p>
      <h1 style="margin:0 0 10px;font-size:24px;font-weight:800;color:{_INK};letter-spacing:-0.03em;">
        Скидання пароля
      </h1>
      <p style="margin:0 0 24px;font-size:15px;color:{_MUTED};line-height:1.65;">
        Натисніть кнопку нижче, щоб встановити новий пароль. Посилання дійсне
        <strong style="color:{_INK};">1 годину</strong>.
      </p>
      {_cta_button("Встановити новий пароль →", reset_url)}
      <p style="margin:24px 0 0;font-size:13px;color:{_MUTED};line-height:1.65;">
        Якщо ви не запитували скидання — проігноруйте цей лист. Пароль залишиться без змін.
      </p>
    """
    return subject, _base_layout(content)
