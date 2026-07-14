import type { Listing } from "@/types/api";

/** Нормалізує listing перед POST /favorites (Pydantic на backend очікує повний об'єкт). */
export function normalizeListingForFavorite(listing: Listing): Listing {
  return {
    ...listing,
    price_history: Array.isArray(listing.price_history) ? listing.price_history : [],
    images: Array.isArray(listing.images) ? listing.images : [],
    fuel: listing.fuel ?? "",
    transmission: listing.transmission ?? "",
    region: listing.region ?? "",
    currency: listing.currency || "UAH",
    is_duplicate: listing.is_duplicate ?? false,
    alternate_sources: Array.isArray(listing.alternate_sources)
      ? listing.alternate_sources
      : [],
    published_at: listing.published_at || new Date().toISOString(),
    found_at: listing.found_at || new Date().toISOString(),
  };
}
