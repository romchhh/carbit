from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from app.services.olx.constants import BASE_URL, REQUEST_TIMEOUT, USER_AGENTS

logger = logging.getLogger(__name__)

IMPERSONATE_TARGETS: tuple[str, ...] = (
    "chrome136",
    "chrome133a",
    "chrome131",
    "chrome124",
    "chrome120",
    "chrome119",
    "safari17_0",
)

_CURL_CODE_RE = re.compile(r"__CURL_HTTP_CODE__:(\d+)\s*$")


@dataclass
class HttpResponse:
    status_code: int
    text: str

    def json(self) -> Any:
        import json

        return json.loads(self.text)


try:
    import curl_cffi

    CURL_CFFI_VERSION = getattr(curl_cffi, "__version__", "?")
    CURL_CFFI_AVAILABLE = True
except ImportError:  # pragma: no cover
    curl_cffi = None  # type: ignore[assignment]
    CURL_CFFI_VERSION = None
    CURL_CFFI_AVAILABLE = False


def transport_summary(*, impersonate: str, proxy: str | None) -> str:
    parts = [
        f"curl_cffi={'yes' if CURL_CFFI_AVAILABLE else 'NO'}",
    ]
    if CURL_CFFI_VERSION:
        parts.append(f"v{CURL_CFFI_VERSION}")
    parts.append(f"impersonate={impersonate}")
    if proxy:
        parts.append("proxy=on")
    return ", ".join(parts)


def impersonate_candidates(primary: str) -> tuple[str, ...]:
    primary = (primary or "chrome131").strip() or "chrome131"
    out: list[str] = [primary]
    for item in IMPERSONATE_TARGETS:
        if item not in out:
            out.append(item)
    return tuple(out)


async def system_curl_get(
    url: str,
    *,
    headers: dict[str, str],
    params: dict | None = None,
    proxy: str | None = None,
) -> HttpResponse:
    """Fallback через системний curl (є в Docker-образі)."""
    full_url = url
    if params:
        sep = "&" if "?" in url else "?"
        full_url = f"{url}{sep}{urlencode(params, doseq=True)}"

    cmd = [
        "curl",
        "-sS",
        "-L",
        "--compressed",
        "--max-time",
        str(max(5, int(REQUEST_TIMEOUT))),
        "-A",
        USER_AGENTS[0],
        "-H",
        f"Accept-Language: {headers.get('Accept-Language', 'uk-UA,uk;q=0.9')}",
        "-H",
        f"Accept: {headers.get('Accept', '*/*')}",
        "-H",
        f"Referer: {headers.get('Referer', BASE_URL + '/')}",
        "-w",
        "\n__CURL_HTTP_CODE__:%{http_code}",
        full_url,
    ]
    if proxy:
        cmd[1:1] = ["--proxy", proxy]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = (stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(err or f"curl exit {proc.returncode}")

    raw = stdout.decode("utf-8", errors="replace")
    match = _CURL_CODE_RE.search(raw)
    if not match:
        raise RuntimeError("curl: missing HTTP status marker")
    status = int(match.group(1))
    body = raw[: match.start()]
    return HttpResponse(status_code=status, text=body)
