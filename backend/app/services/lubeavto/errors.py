from __future__ import annotations


class LubeAvtoError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.request = request
