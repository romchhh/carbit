def _base_layout(content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Carbit</title>
</head>
<body style="margin:0;padding:0;background:#F7F8FA;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F8FA;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:20px;border:1px solid #E4E6EA;overflow:hidden;box-shadow:0 4px 24px rgba(10,12,14,0.06);">
          <tr>
            <td style="background:linear-gradient(135deg,#0A0C0E 0%,#1A1D21 100%);padding:28px 32px;">
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td style="width:40px;height:40px;background:rgba(0,200,150,0.2);border-radius:50%;text-align:center;vertical-align:middle;">
                    <span style="color:#00C896;font-size:18px;font-weight:bold;">✦</span>
                  </td>
                  <td style="padding-left:12px;">
                    <span style="color:#ffffff;font-size:18px;font-weight:700;letter-spacing:-0.02em;">Carbit</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              {content}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px 28px;border-top:1px solid #E4E6EA;background:#F7F8FA;">
              <p style="margin:0;font-size:12px;color:#6B7280;line-height:1.6;text-align:center;">
                © 2026 Carbit · Агрегатор авторинку України<br/>
                <a href="https://carbit.telebots.site" style="color:#00A47C;text-decoration:none;">carbit.telebots.site</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def verification_code_email(name: str, code: str) -> tuple[str, str]:
    subject = f"{code} — код підтвердження Carbit"
    content = f"""
      <p style="margin:0 0 8px;font-size:14px;color:#6B7280;">Привіт, {name}!</p>
      <h1 style="margin:0 0 12px;font-size:22px;font-weight:800;color:#0A0C0E;letter-spacing:-0.02em;">
        Підтвердіть email
      </h1>
      <p style="margin:0 0 28px;font-size:14px;color:#6B7280;line-height:1.6;">
        Введіть цей код на сторінці реєстрації. Він дійсний <strong style="color:#0A0C0E;">10 хвилин</strong>.
      </p>
      <div style="background:#F7F8FA;border:2px dashed #E4E6EA;border-radius:16px;padding:24px;text-align:center;margin-bottom:24px;">
        <span style="font-size:36px;font-weight:900;letter-spacing:0.35em;color:#0A0C0E;font-family:monospace;">
          {code}
        </span>
      </div>
      <p style="margin:0;font-size:13px;color:#6B7280;line-height:1.6;">
        Якщо ви не реєструвались в Carbit — просто проігноруйте цей лист.
      </p>
    """
    return subject, _base_layout(content)


def welcome_email(name: str, dashboard_url: str) -> tuple[str, str]:
    first_name = name.split()[0] if name.strip() else name
    subject = f"Ласкаво просимо в Carbit, {first_name}! 🚗"
    content = f"""
      <p style="margin:0 0 8px;font-size:14px;color:#6B7280;">Вітаємо, {first_name}!</p>
      <h1 style="margin:0 0 12px;font-size:22px;font-weight:800;color:#0A0C0E;letter-spacing:-0.02em;">
        Ваш акаунт активовано
      </h1>
      <p style="margin:0 0 28px;font-size:14px;color:#6B7280;line-height:1.6;">
        Тепер Carbit моніторить AUTO.RIA, OLX і Telegram за вас — і сповіщає про нові авто раніше за конкурентів.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
        <tr>
          <td style="padding:14px 16px;background:#F7F8FA;border-radius:12px;margin-bottom:8px;">
            <span style="font-size:20px;">🔍</span>
            <strong style="display:block;margin-top:6px;font-size:14px;color:#0A0C0E;">Створіть перший пошук</strong>
            <span style="font-size:12px;color:#6B7280;">Налаштуйте фільтри — ми знайдемо авто автоматично</span>
          </td>
        </tr>
        <tr><td style="height:8px;"></td></tr>
        <tr>
          <td style="padding:14px 16px;background:#F7F8FA;border-radius:12px;">
            <span style="font-size:20px;">⚡</span>
            <strong style="display:block;margin-top:6px;font-size:14px;color:#0A0C0E;">Отримуйте сповіщення</strong>
            <span style="font-size:12px;color:#6B7280;">Нові оголошення — за лічені хвилини</span>
          </td>
        </tr>
      </table>
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td align="center">
            <a href="{dashboard_url}"
               style="display:inline-block;background:#00C896;color:#ffffff;font-size:14px;font-weight:700;
                      text-decoration:none;padding:14px 32px;border-radius:999px;box-shadow:0 4px 14px rgba(0,200,150,0.35);">
              Перейти до кабінету →
            </a>
          </td>
        </tr>
      </table>
      <p style="margin:24px 0 0;font-size:12px;color:#6B7280;text-align:center;line-height:1.6;">
        7 днів безкоштовно · Без прив'язки карти
      </p>
    """
    return subject, _base_layout(content)


def password_reset_email(name: str, reset_url: str) -> tuple[str, str]:
    first_name = name.split()[0] if name.strip() else name
    subject = "Скидання пароля Carbit"
    content = f"""
      <p style="margin:0 0 8px;font-size:14px;color:#6B7280;">Привіт, {first_name}!</p>
      <h1 style="margin:0 0 12px;font-size:22px;font-weight:800;color:#0A0C0E;letter-spacing:-0.02em;">
        Скидання пароля
      </h1>
      <p style="margin:0 0 28px;font-size:14px;color:#6B7280;line-height:1.6;">
        Натисніть кнопку нижче, щоб встановити новий пароль. Посилання дійсне <strong style="color:#0A0C0E;">1 годину</strong>.
      </p>
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td align="center">
            <a href="{reset_url}"
               style="display:inline-block;background:#00C896;color:#ffffff;font-size:14px;font-weight:700;
                      text-decoration:none;padding:14px 32px;border-radius:999px;box-shadow:0 4px 14px rgba(0,200,150,0.35);">
              Встановити новий пароль →
            </a>
          </td>
        </tr>
      </table>
      <p style="margin:24px 0 0;font-size:12px;color:#6B7280;line-height:1.6;">
        Якщо ви не запитували скидання — проігноруйте цей лист. Пароль залишиться без змін.
      </p>
    """
    return subject, _base_layout(content)
