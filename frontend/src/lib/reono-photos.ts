import { listings as listingsApi } from "@/lib/api";
import { resolveListingImages } from "@/lib/listing-image-url";
import type { Listing } from "@/types/api";

const cache = new Map<string, Promise<string[]>>();
const REONO_CDN = /stx\.reono\.ua/i;
const PLACEHOLDER = /no[_-]?img/i;

export function countValidReonoImages(images: string[] | null | undefined): number {
  return (images ?? []).filter(url => REONO_CDN.test(url) && !PLACEHOLDER.test(url)).length;
}

export function listingNeedsReonoPhotos(listing: Listing): boolean {
  if ((listing.source || "").toLowerCase() !== "reono") return false;
  if (!listing.url?.trim()) return false;
  return countValidReonoImages(listing.images) < 2;
}

/** У модалці завжди тягнемо повну галерею зі сторінки REONO. */
export function listingShouldFetchReonoGallery(listing: Listing): boolean {
  if ((listing.source || "").toLowerCase() !== "reono") return false;
  return Boolean(listing.url?.trim());
}

export async function fetchReonoListingPhotos(url: string): Promise<string[]> {
  const key = url.trim();
  const existing = cache.get(key);
  if (existing) return existing;

  const promise = listingsApi
    .reonoPhotos(key)
    .then(result => {
      const images = resolveListingImages(result.images);
      if (!images.length) cache.delete(key);
      return images;
    })
    .catch(() => {
      cache.delete(key);
      return [] as string[];
    });

  cache.set(key, promise);
  return promise;
}

export async function ensureReonoPhotosDeduped(listing: Listing): Promise<string[]> {
  if (!listing.url?.trim()) return resolveListingImages(listing.images);
  const fetched = await fetchReonoListingPhotos(listing.url);
  if (fetched.length) return fetched;
  return resolveListingImages(listing.images);
}
