from __future__ import annotations

USD_TO_UAH = 45
EUR_TO_UAH = 44

DISPLAY_CURRENCIES = frozenset({"UAH", "USD", "EUR"})


def normalize_currency(currency: str | None) -> str:
    if not currency:
        return "UAH"
    cur = currency.strip().upper().replace(".", "")
    if cur in {"UAH", "ГРН", "UA", "ГРН."}:
        return "UAH"
    if cur in {"USD", "$", "US"}:
        return "USD"
    if cur in {"EUR", "€", "EU", "EURO"}:
        return "EUR"
    return cur


def resolve_display_currency(currency: str | None) -> str:
    """Валюта відображення для користувача: UAH | USD | EUR."""
    cur = normalize_currency(currency)
    return cur if cur in DISPLAY_CURRENCIES else "UAH"


def resolve_filter_currency(currency: str | None) -> str:
    """Валюта діапазону ціни у фільтрі. Без значення — UAH."""
    if not currency:
        return "UAH"
    cur = normalize_currency(currency)
    return cur if cur in DISPLAY_CURRENCIES else "UAH"


def currency_label(currency: str | None) -> str:
    cur = resolve_display_currency(currency)
    if cur == "USD":
        return "$"
    if cur == "EUR":
        return "€"
    return "грн"


def infer_currency(amount: float, currency: str | None, text: str = "") -> str:
    """
    Визначає валюту оголошення.
    Ціни в БД/результатах зберігаємо в грн — USD/EUR конвертуємо перед порівнянням.
    """
    if currency:
        return normalize_currency(currency)

    text_low = (text or "").lower()
    if any(marker in text_low for marker in ("грн", "uah", "гривн")):
        return "UAH"
    if "€" in text or "eur" in text_low:
        return "EUR"
    if any(marker in text_low for marker in ("$", "usd", "дол", "у.е", "у. e", "mmr", "💲", "💵", "💰")):
        return "USD"

    if amount >= 300_000:
        return "UAH"
    if amount <= 100_000:
        return "USD"
    return "UAH"


def to_uah(amount: float | int | None, currency: str | None, *, text: str = "") -> int:
    if amount is None:
        return 0
    value = float(amount)
    cur = infer_currency(value, currency, text)
    if cur == "USD":
        return int(round(value * USD_TO_UAH))
    if cur == "EUR":
        return int(round(value * EUR_TO_UAH))
    return int(round(value))


def from_uah(amount_uah: float | int | None, target_currency: str | None) -> int:
    """Конвертує ціну з грн (як у БД) у валюту відображення."""
    if amount_uah is None:
        return 0
    value = float(amount_uah)
    cur = resolve_display_currency(target_currency)
    if cur == "USD":
        return int(round(value / USD_TO_UAH))
    if cur == "EUR":
        return int(round(value / EUR_TO_UAH))
    return int(round(value))


def format_price_uah(amount_uah: float | int | None, target_currency: str | None) -> str:
    """Рядок ціни для Telegram / текстів: '12 500 $'."""
    amount = from_uah(amount_uah, target_currency)
    label = currency_label(target_currency)
    formatted = f"{amount:,}".replace(",", " ")
    return f"{formatted} {label}"


def filter_price_to_uah(amount: int | None, currency: str | None) -> int | None:
    """Переводить межу фільтра ціни в грн для пост-фільтрів (OLX/Telegram/БД)."""
    if amount is None:
        return None
    return to_uah(amount, resolve_filter_currency(currency))
