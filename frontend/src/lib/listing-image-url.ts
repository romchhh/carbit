import { getApiUrl } from "@/lib/api-url";

const REONO_CDN_HOST = "stx.reono.ua";

function apiOrigin(): string {
  const api = getApiUrl();
  if (api.startsWith("http://") || api.startsWith("https://")) {
    return api.replace(/\/api\/v1\/?$/, "");
  }
  return "";
}

/** Проксі через backend для CDN REONO (hotlink-захист). */
export function reonoImageProxyUrl(url: string): string {
  const origin = apiOrigin();
  const base = origin || "";
  return `${base}/api/v1/external-media?url=${encodeURIComponent(url)}`;
}

function isReonoCdnUrl(url: string): boolean {
  try {
    return new URL(url).hostname.toLowerCase() === REONO_CDN_HOST;
  } catch {
    return false;
  }
}

/** Абсолютний URL для /api/v1/telegram-media/… (dev: backend на :8000, prod: same-origin proxy). */
export function resolveListingImageUrl(url: string | null | undefined): string {
  if (!url?.trim()) return "";
  const value = url.trim();
  if (isReonoCdnUrl(value)) {
    return reonoImageProxyUrl(value);
  }
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  if (!value.startsWith("/api/")) return value;

  const api = getApiUrl();
  if (api.startsWith("http://") || api.startsWith("https://")) {
    const origin = api.replace(/\/api\/v1\/?$/, "");
    return `${origin}${value}`;
  }
  return value;
}

export function resolveListingImages(urls: string[] | null | undefined): string[] {
  if (!Array.isArray(urls)) return [];
  return urls.map(resolveListingImageUrl).filter(Boolean);
}
