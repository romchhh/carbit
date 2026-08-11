import { getApiUrl } from "@/lib/api-url";

/** Абсолютний URL для /api/v1/telegram-media/… (dev: backend на :8000, prod: same-origin proxy). */
export function resolveListingImageUrl(url: string | null | undefined): string {
  if (!url?.trim()) return "";
  const value = url.trim();
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
