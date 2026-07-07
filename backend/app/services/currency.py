from __future__ import annotations

USD_TO_UAH = 41
EUR_TO_UAH = 44


def normalize_currency(currency: str | None) -> str:
    if not currency:
        return "UAH"
    cur = currency.strip().upper().replace(".", "")
    if cur in {"UAH", "ГРН", "UA"}:
        return "UAH"
    if cur in {"USD", "$", "US"}:
        return "USD"
    if cur in {"EUR", "€", "EU"}:
        return "EUR"
    return cur


def infer_currency(amount: float, currency: str | None, text: str = "") -> str:
    """
    Визначає валюту оголошення.
    Пошук користувача в грн — тому USD/EUR конвертуємо перед порівнянням.
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

    # Типові діапазони: локальний ринок UAH vs import USD
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
