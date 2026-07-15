from __future__ import annotations


class BazaGaiError(Exception):
    def __init__(self, message: str, *, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BazaGaiNotConfigured(BazaGaiError):
    def __init__(self):
        super().__init__("Перевірка VIN через Базу ДАІ не налаштована", status_code=503)


class BazaGaiNotFound(BazaGaiError):
    def __init__(self, ref: str = ""):
        hint = f" ({ref})" if ref else ""
        super().__init__(
            f"VIN не знайдено в Базі ДАІ{hint}. Дані доступні здебільшого для реєстрацій з 2021 року.",
            status_code=404,
        )


class BazaGaiRateLimited(BazaGaiError):
    def __init__(self):
        super().__init__(
            "Вичерпано ліміт запитів до Бази ДАІ. Спробуйте пізніше.",
            status_code=429,
        )
