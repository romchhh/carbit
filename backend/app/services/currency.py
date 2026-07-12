from __future__ import annotations

USD_TO_UAH = 45
EUR_TO_UAH = 44

DISPLAY_CURRENCIES = frozenset({"UAH", "USD", "EUR"})
DEFAULT_DISPLAY_CURRENCY = "USD"


def normalize_currency(currency: str | None) -> str:
    if not currency:
        return DEFAULT_DISPLAY_CURRENCY
    cur = currency.strip().upper().replace(".", "")
    if cur in {"UAH", "ГРН", "UA", "ГРН."}:
        return "UAH"
    if cur in {"USD", "$", "US"}:
        return "USD"
    if cur in {"EUR", "€", "EU", "EURO"}:
        return "EUR"
    return cur


def resolve_display_currency(currency: str | None) -> str:
    """Валюта відображення для користувача: UAH | USD | EUR. Порожнє → USD."""
    if not currency:
        return DEFAULT_DISPLAY_CURRENCY
    cur = normalize_currency(currency)
    return cur if cur in DISPLAY_CURRENCIES else DEFAULT_DISPLAY_CURRENCY


def resolve_filter_currency(currency: str | None) -> str:
    """Валюта діапазону ціни у фільтрі. Без значення — USD."""
    if not currency:
        return DEFAULT_DISPLAY_CURRENCY
    cur = normalize_currency(currency)
    return cur if cur in DISPLAY_CURRENCIES else DEFAULT_DISPLAY_CURRENCY


def currency_label(currency: str | None) -> str:
    cur = resolve_display_currency(currency)
    if cur == "USD":
        return "$"
    if cur == "EUR":
        return "€"
    return "грн"


def infer_currency(amount: float, currency: str | None, text: str = "") -> str:
    """Визначає валюту оголошення з явного поля або з тексту/величини."""
    if currency:
        cur = normalize_currency(currency)
        if cur in DISPLAY_CURRENCIES:
            return cur

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
    """Переводить суму в грн для порівнянь/сортування."""
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
    """Конвертує ціну з грн у валюту відображення."""
    if amount_uah is None:
        return 0
    value = float(amount_uah)
    cur = resolve_display_currency(target_currency)
    if cur == "USD":
        return int(round(value / USD_TO_UAH))
    if cur == "EUR":
        return int(round(value / EUR_TO_UAH))
    return int(round(value))


def convert_price(
    amount: float | int | None,
    from_currency: str | None,
    to_currency: str | None,
    *,
    text: str = "",
) -> int:
    """
    Конвертує ціну між валютами.
    Якщо валюти збігаються — повертає оригінал без округлення через курс
    (щоб 16 300 $ з OLX лишались 16 300 $, а не 16 131 $).
    """
    if amount is None:
        return 0
    src = infer_currency(float(amount), from_currency, text)
    dst = resolve_display_currency(to_currency)
    if src == dst:
        return int(round(float(amount)))
    return from_uah(to_uah(amount, src, text=text), dst)


def format_display_price(
    amount: float | int | None,
    from_currency: str | None,
    to_currency: str | None,
    *,
    text: str = "",
) -> str:
    """Рядок ціни: '16 300 $' без зайвого round-trip, якщо валюти збігаються."""
    value = convert_price(amount, from_currency, to_currency, text=text)
    label = currency_label(to_currency)
    formatted = f"{value:,}".replace(",", " ")
    return f"{formatted} {label}"


def format_price_uah(amount_uah: float | int | None, target_currency: str | None) -> str:
    """Сумісність: amount уже в грн."""
    return format_display_price(amount_uah, "UAH", target_currency)


def filter_price_to_uah(amount: int | None, currency: str | None) -> int | None:
    """Переводить межу фільтра ціни в грн для пост-фільтрів."""
    if amount is None:
        return None
    return to_uah(amount, resolve_filter_currency(currency))


def listing_price_uah(amount: float | int | None, currency: str | None) -> int:
    """Ціна оголошення в грн для сортування/фільтрів."""
    return to_uah(amount, currency)
