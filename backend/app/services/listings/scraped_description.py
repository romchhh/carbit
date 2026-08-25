"""Завантаження описів оголошень для скрейпінгових джерел (REONO, Car Market)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_CONCURRENCY = 6


async def fetch_descriptions_by_url(
    urls: Iterable[str],
    *,
    fetch_html: Callable[[httpx.AsyncClient, str], str],
    parse_description: Callable[[str], str | None],
    headers: dict[str, str],
    concurrency: int = _DEFAULT_CONCURRENCY,
) -> dict[str, str]:
    unique_urls = [url for url in dict.fromkeys(url for url in urls if url)]
    if not unique_urls:
        return {}

    semaphore = asyncio.Semaphore(max(1, concurrency))
    results: dict[str, str] = {}

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=20.0,
        limits=httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency),
    ) as client:

        async def _one(url: str) -> None:
            async with semaphore:
                try:
                    html = await fetch_html(client, url)
                except Exception:
                    logger.debug("description fetch failed for %s", url, exc_info=True)
                    return
                description = parse_description(html)
                if description:
                    results[url] = description

        await asyncio.gather(*(_one(url) for url in unique_urls))

    return results


def apply_descriptions(
    listings: list,
    descriptions: dict[str, str],
    *,
    source_key: str,
) -> list:
    if not descriptions:
        return listings

    updated: list = []
    for listing in listings:
        description = descriptions.get(getattr(listing, "url", "") or "")
        if not description:
            updated.append(listing)
            continue
        source_data = dict(getattr(listing, "source_data", None) or {})
        nested = dict(source_data.get(source_key) or {})
        nested["description"] = description
        source_data[source_key] = nested
        updated.append(
            listing.model_copy(
                update={
                    "description": description,
                    "source_data": source_data,
                }
            )
        )
    return updated
