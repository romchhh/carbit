import type { Listing } from "@/types/api";

export const SIGNIFICANT_PRICE_DROP_PERCENT = 5;

export type ListingPriceDrop = {
  previousPrice: number;
  dropPercent: number;
  droppedAt?: string | null;
};

export function resolveListingPriceDrop(listing: Listing): ListingPriceDrop | null {
  const previousPrice = Number(listing.previous_price) || 0;
  const dropPercent = Number(listing.price_drop_percent) || 0;
  if (previousPrice <= 0 || dropPercent < SIGNIFICANT_PRICE_DROP_PERCENT) {
    return null;
  }
  return {
    previousPrice,
    dropPercent,
    droppedAt: listing.price_dropped_at ?? null,
  };
}

export function formatDropPercent(value: number): string {
  const rounded = Math.round(value);
  if (Math.abs(value - rounded) < 0.05) return String(rounded);
  return value.toFixed(1).replace(/\.0$/, "");
}
