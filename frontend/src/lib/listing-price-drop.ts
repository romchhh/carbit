import type { Listing } from "@/types/api";

export const SIGNIFICANT_PRICE_DROP_PERCENT = 5;

export type ListingPriceDrop = {
  previousPrice: number;
  previousCurrency?: string | null;
  dropPercent: number;
  droppedAt?: string | null;
};

function dropFromHistory(listing: Listing): ListingPriceDrop | null {
  const history = Array.isArray(listing.price_history) ? listing.price_history : [];
  if (history.length === 0) return null;
  const last = history[history.length - 1];
  if (!last || typeof last !== "object") return null;
  const previousPrice = Number((last as { price?: unknown }).price) || 0;
  const current = Number(listing.price) || 0;
  if (previousPrice <= 0 || current <= 0 || current >= previousPrice) return null;
  const dropPercent = ((previousPrice - current) / previousPrice) * 100;
  if (dropPercent < SIGNIFICANT_PRICE_DROP_PERCENT) return null;
  const at = (last as { at?: unknown }).at;
  return {
    previousPrice,
    previousCurrency:
      typeof (last as { currency?: unknown }).currency === "string"
        ? (last as { currency: string }).currency
        : listing.previous_currency ?? listing.currency ?? null,
    dropPercent: Math.round(dropPercent * 10) / 10,
    droppedAt: typeof at === "string" ? at : listing.price_dropped_at ?? null,
  };
}

export function resolveListingPriceDrop(listing: Listing): ListingPriceDrop | null {
  const previousPrice = Number(listing.previous_price) || 0;
  const dropPercent = Number(listing.price_drop_percent) || 0;
  if (previousPrice > 0 && dropPercent >= SIGNIFICANT_PRICE_DROP_PERCENT) {
    return {
      previousPrice,
      previousCurrency: listing.previous_currency ?? listing.currency ?? null,
      dropPercent,
      droppedAt: listing.price_dropped_at ?? null,
    };
  }
  return dropFromHistory(listing);
}

export function formatDropPercent(value: number): string {
  const rounded = Math.round(value);
  if (Math.abs(value - rounded) < 0.05) return String(rounded);
  return value.toFixed(1).replace(/\.0$/, "");
}
