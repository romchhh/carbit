from __future__ import annotations

from urllib.parse import urlencode


def http_request_label(
    method: str,
    url: str,
    *,
    params: dict | None = None,
) -> str:
    if params:
        query = urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
        if query:
            sep = "&" if "?" in url else "?"
            return f"{method} {url}{sep}{query}"
    return f"{method} {url}"


def error_parts(exc: Exception) -> tuple[str, str | None]:
    message = str(exc).strip() or exc.__class__.__name__
    request = getattr(exc, "request", None)
    if isinstance(request, str) and request.strip():
        return message, request.strip()
    return message, None
