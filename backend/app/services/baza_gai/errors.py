from __future__ import annotations


class BazaGaiError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class BazaGaiNotConfigured(BazaGaiError):
    def __init__(self):
        super().__init__("Перевірка VIN тимчасово недоступна (API ключ не налаштовано)", status_code=503)


class BazaGaiNotFound(BazaGaiError):
    def __init__(self, vin: str):
        super().__init__(f"За VIN {vin} нічого не знайдено в Базі ДАІ", status_code=404)


class BazaGaiRateLimited(BazaGaiError):
    def __init__(self):
        super().__init__("Ліміт запитів до Бази ДАІ вичерпано. Спробуйте пізніше.", status_code=429)
