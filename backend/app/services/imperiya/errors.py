class ImperiyaError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ImperiyaBrandNotFound(ValueError):
    """Марки немає в каталозі Імперія Авто (вантажівки тощо) — порожній результат без помилки."""
