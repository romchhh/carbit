import { resolveSiteUrl } from "@/lib/site-metadata";
import { MAX_COMPARE, buildCompareShareUrl } from "@/lib/listing-compare";
import type { Listing } from "@/types/api";

function siteOrigin(): string {
  if (typeof window !== "undefined" && window.location?.origin) {
    return window.location.origin;
  }
  return resolveSiteUrl();
}

/**
 * Id з URL `/app/listing/...` або посилання AUTO.RIA.
 * Деякі месенджери склеюють title/text до посилання — відрizaємо все після пробілу.
 */
export function normalizeListingIdParam(raw: string | null | undefined): string {
  let value = (raw || "").trim();
  if (!value) return "";
  try {
    value = decodeURIComponent(value);
  } catch {
    /* лишаємо як є */
  }
  value = value.trim();

  const autoRiaNew = value.match(/auto\.ria\.com\/(?:uk\/)?(?:newauto\/)?auto[-/](\d+)\.html/i);
  if (autoRiaNew?.[1]) return `new_auto_ria_${autoRiaNew[1]}`;

  const autoRiaUsed = value.match(/auto\.ria\.com\/(?:uk\/)?auto_[^/?#]+_(\d+)\.html/i);
  if (autoRiaUsed?.[1]) return `auto_ria_${autoRiaUsed[1]}`;

  const trailingId = value.match(/_(\d+)\.html(?:[/?#]|$)/i);
  if (trailingId?.[1] && value.includes("auto.ria")) {
    return `auto_ria_${trailingId[1]}`;
  }

  if (/^new_auto_ria_\d+$/.test(value) || /^auto_ria_\d+$/.test(value)) {
    return value;
  }

  const first = value.split(/\s+/)[0] || "";
  return first.replace(/[/?#]+$/g, "");
}

/** Публічне посилання на картку авто на Carbit. */
export function buildListingShareUrl(listingId: string): string {
  const id = normalizeListingIdParam(listingId);
  if (!id) return `${siteOrigin()}/app/dashboard`;
  return `${siteOrigin()}/app/listing/${encodeURIComponent(id)}`;
}

/** Посилання на підбірку кількох авто (порівняння / share). */
export function buildListingsSelectionShareUrl(
  listings: Listing[],
  shareId?: string | null,
): string {
  const items = listings.filter(item => item?.id).slice(0, MAX_COMPARE);
  if (items.length === 1) {
    return buildListingShareUrl(items[0].id);
  }
  return buildCompareShareUrl(items, shareId);
}

export type ShareResult = "shared" | "copied" | "failed";

/** Web Share API або копіювання в буфер. */
export async function shareOrCopyUrl(options: {
  url: string;
  title?: string;
  text?: string;
}): Promise<ShareResult> {
  const { url, title } = options;
  if (!url) return "failed";

  if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
    try {
      // Лише url (+ title). Не передаємо text — месенджери часто
      // склеюють text до url і ламають path (/listing/id Title…).
      await navigator.share({
        title: title || "Carbit",
        url,
      });
      return "shared";
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return "failed";
      }
    }
  }

  try {
    await navigator.clipboard.writeText(url);
    return "copied";
  } catch {
    return "failed";
  }
}

export function listingShareTitle(listing: Listing): string {
  const bits = [listing.title, listing.year > 0 ? String(listing.year) : ""]
    .map(v => (v || "").trim())
    .filter(Boolean);
  return bits.join(" · ") || "Авто на Carbit";
}
