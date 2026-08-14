from __future__ import annotations


class AutohelperbotError(Exception):
    def __init__(self, message: str, *, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AutohelperbotNotFound(AutohelperbotError):
    def __init__(self, vin: str = ""):
        hint = f" ({vin})" if vin else ""
        super().__init__(
            f"VIN не знайдено в аукціонній історії{hint}.",
            status_code=404,
        )
