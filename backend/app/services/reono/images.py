from __future__ import annotations

import json
import re
from typing import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.services.reono.constants import REONO_BASE_URL

_NO_IMG_MARKERS = ("no_img", "no-img", "placeholder")
_STX_HOST = "stx.reono.ua"
_PREFERRED_SIZES = ("1582/1186", "791/593", "720/516", "360/258", "200/150", "144/108", "100/75")
_TOKEN_RE = re.compile(r"stx\.reono\.ua/\d+/\d+/(.+)$", re.IGNORECASE)
_BG_IMAGE_RE = re.compile(r"url\((['\"]?)([^)'\"]+)\1\)", re.IGNORECASE)


def _is_placeholder(url: str) -> bool:
    lowered = url.lower()
    return any(marker in lowered for marker in _NO_IMG_MARKERS)


def normalize_reono_image_url(src: object) -> str | None:
    if not src or not isinstance(src, str):
        return None
    value = src.strip()
    if not value or value.startswith("data:"):
        return None
    if _is_placeholder(value):
        return None
    if value.startswith("//"):
        value = f"https:{value}"
    if value.startswith("/"):
        value = REONO_BASE_URL + value
    if not value.startswith("http"):
        return None
    return value


def reono_photo_token(url: str) -> str | None:
    match = _TOKEN_RE.search(url)
    if match:
        return match.group(1)
    if _STX_HOST in url.lower():
        return url
    return None


def reono_preferred_image_url(url: str) -> str:
    """Повертає URL найбільшого доступного розміру для того самого фото."""
    token = reono_photo_token(url)
    if not token or not _TOKEN_RE.search(url):
        return url
    return f"https://{_STX_HOST}/{_PREFERRED_SIZES[0]}/{token}"


def reono_fallback_urls(url: str) -> list[str]:
    """Варіанти розмірів одного фото на CDN REONO (для retry проксі)."""
    token = reono_photo_token(url)
    if not token or not _TOKEN_RE.search(url):
        return [url]
    candidates = [f"https://{_STX_HOST}/{size}/{token}" for size in _PREFERRED_SIZES]
    if url not in candidates:
        candidates.insert(0, url)
    seen: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.append(item)
    return seen


def valid_reono_cdn_urls(urls: Iterable[str]) -> list[str]:
    return [url for url in urls if is_reono_cdn_url(url) and not _is_placeholder(url)]


def _add_url(urls: dict[str, str], raw: object, *, size_hint: str | None = None) -> None:
    normalized = normalize_reono_image_url(raw)
    if not normalized:
        return
    token = reono_photo_token(normalized)
    if not token:
        return
    preferred = (
        f"https://{_STX_HOST}/{_PREFERRED_SIZES[0]}/{token}"
        if _TOKEN_RE.search(normalized)
        else normalized
    )
    current = urls.get(token)
    if not current:
        urls[token] = preferred
        return
    if size_hint and size_hint in current:
        return
    if "791/593" in normalized or "1582/1186" in normalized:
        urls[token] = preferred


def _collect_from_srcset(raw: object, urls: dict[str, str]) -> None:
    if not raw:
        return
    for part in str(raw).split(","):
        chunk = part.strip().split()
        if not chunk:
            continue
        candidate = chunk[0]
        if _is_placeholder(candidate):
            continue
        size_hint = chunk[1] if len(chunk) > 1 else None
        _add_url(urls, candidate, size_hint=size_hint)


def _collect_from_tag(tag: Tag, urls: dict[str, str]) -> None:
    for attr in ("data-image-large", "data-image-normal", "data-src", "src"):
        _add_url(urls, tag.get(attr))
    # data-srcset містить повнорозмірні URL; srcset часто — placeholder до lazy-load.
    _collect_from_srcset(tag.get("data-srcset"), urls)
    _collect_from_srcset(tag.get("srcset"), urls)
    style = tag.get("style") or ""
    for match in _BG_IMAGE_RE.finditer(style):
        _add_url(urls, match.group(2))


def _merge_urls(urls: dict[str, str], found: Iterable[str]) -> None:
    for url in found:
        token = reono_photo_token(url)
        if token:
            urls[token] = reono_preferred_image_url(url)


def extract_image_urls_from_node(node: Tag) -> list[str]:
    urls: dict[str, str] = {}
    for el in node.select(
        ".car-card__lazy-picture, [data-image-large], [data-image-normal], [data-card-lazy-picture]"
    ):
        _collect_from_tag(el, urls)
    for el in node.select("picture, source[data-srcset], source[srcset]"):
        if el.name == "picture":
            for child in el.select("source[data-srcset], source[srcset], img"):
                _collect_from_tag(child, urls)
        else:
            _collect_from_tag(el, urls)
    for el in node.select("img"):
        _collect_from_tag(el, urls)
    for el in node.select('[style*="background-image"]'):
        style = el.get("style") or ""
        for match in _BG_IMAGE_RE.finditer(style):
            _add_url(urls, match.group(2))
    return list(urls.values())


def extract_card_image_urls(card: Tag) -> list[str]:
    urls: dict[str, str] = {}
    for slide in card.select(".car-card__slide"):
        _merge_urls(urls, extract_image_urls_from_node(slide))
    if not urls:
        _merge_urls(urls, extract_image_urls_from_node(card))
    return list(urls.values())


def extract_card_cover_image(card: Tag) -> str | None:
    urls = extract_card_image_urls(card)
    return urls[0] if urls else None


def parse_detail_images(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: dict[str, str] = {}

    gallery_roots = soup.select(
        ".description-car-main-big__wrapper, .description-car-main-big__slider, "
        ".description-car-main__sliders"
    )
    for gallery in gallery_roots:
        _merge_urls(urls, extract_image_urls_from_node(gallery))

    if not urls:
        _merge_urls(urls, extract_image_urls_from_node(soup))

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.get_text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        image = data.get("image")
        if isinstance(image, str):
            _add_url(urls, reono_preferred_image_url(image))
        elif isinstance(image, list):
            for item in image:
                if isinstance(item, str):
                    _add_url(urls, reono_preferred_image_url(item))

    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        _add_url(urls, reono_preferred_image_url(str(og["content"])))

    return list(urls.values())[:30]


def is_reono_cdn_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    return host.lower() == _STX_HOST


def proxyable_reono_urls(urls: Iterable[str]) -> list[str]:
    return [url for url in urls if is_reono_cdn_url(url)]
