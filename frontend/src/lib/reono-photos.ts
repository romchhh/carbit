import { listings as listingsApi } from "@/lib/api";
import { resolveListingImages } from "@/lib/listing-image-url";
import type { Listing } from "@/types/api";

const cache = new Map<string, Promise<string[]>>();

export function listingNeedsReonoPhotos(listing: Listing): boolean {
  if ((listing.source || "").toLowerCase() !== "reono") return false;
  if (!listing.url?.trim()) return false;
  return (listing.images?.length ?? 0) < 2;
}

export async function fetchReonoListingPhotos(url: string): Promise<string[]> {
  const key = url.trim();
  const existing = cache.get(key);
  if (existing) return existing;

  const promise = listingsApi
    .reonoPhotos(key)
    .then(result => resolveListingImages(result.images))
    .catch(() => [] as string[]);

  cache.set(key, promise);
  return promise;
}

export async function ensureReonoPhotosDeduped(listing: Listing): Promise<string[]> {
  if (!listing.url?.trim()) return resolveListingImages(listing.images);
  return fetchReonoListingPhotos(listing.url);
}
