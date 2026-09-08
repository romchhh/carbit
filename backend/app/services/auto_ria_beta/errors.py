from __future__ import annotations


class AutoRiaBetaError(Exception):
    def __init__(self, message: str, *, request: str | None = None):
        super().__init__(message)
        self.request = request or ""
