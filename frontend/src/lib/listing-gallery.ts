import { listings as listingsApi } from "@/lib/api";
import { resolveListingImages } from "@/lib/listing-image-url";
import {
  ensureReonoPhotosDeduped,
  listingNeedsReonoPhotos,
  listingShouldFetchReonoGallery,
} from "@/lib/reono-photos";
import type { Listing } from "@/types/api";

const cache = new Map<string, Promise<Partial<Listing>>>();

const GALLERY_SOURCES = new Set(["auto_ria", "olx", "imperiya"]);

function cacheKey(listing: Listing): string {
  return `${listing.source}:${listing.id}:${listing.url ?? ""}`;
}

function countValidImages(images: string[] | null | undefined): number {
  return (images ?? []).filter(url => url?.trim()).length;
}

export function listingNeedsGalleryHydration(listing: Listing): boolean {
  const source = (listing.source || "").toLowerCase();
  if (source === "reono") return listingNeedsReonoPhotos(listing);
  if (!GALLERY_SOURCES.has(source)) return false;
  if (!listing.id && !listing.url) return false;
  return countValidImages(listing.images) < 2;
}

/** У модалці — повна галерея для маркетплейсів. */
export function listingShouldFetchGallery(listing: Listing): boolean {
  const source = (listing.source || "").toLowerCase();
  if (source === "reono") return listingShouldFetchReonoGallery(listing);
  if (!GALLERY_SOURCES.has(source)) return false;
  return Boolean(listing.id || listing.url);
}

function mergeGalleryIntoListing(listing: Listing, patch: Partial<Listing>): Listing {
  const next: Listing = { ...listing, ...patch };
  if (patch.images?.length) {
    next.images = patch.images;
  }
  return next;
}

export async function ensureListingGallery(listing: Listing): Promise<Listing> {
  const source = (listing.source || "").toLowerCase();

  if (source === "reono") {
    const images = await ensureReonoPhotosDeduped(listing);
    return images.length ? { ...listing, images } : listing;
  }

  if (!GALLERY_SOURCES.has(source)) return listing;

  const key = cacheKey(listing);
  const existing = cache.get(key);
  if (existing) {
    const patch = await existing;
    return mergeGalleryIntoListing(listing, patch);
  }

  const promise = listingsApi
    .fetchGallery({
      source,
      listing_id: listing.id,
      url: listing.url ?? undefined,
      images: listing.images ?? [],
    })
    .then(result => {
      const images = resolveListingImages(result.images);
      if (!images.length) {
        cache.delete(key);
        return {} as Partial<Listing>;
      }
      return {
        images,
        seller_name: result.seller_name ?? listing.seller_name,
        seller_phone: result.seller_phone ?? listing.seller_phone,
        seller_telegram: result.seller_telegram ?? listing.seller_telegram,
        seller_url: result.seller_url ?? listing.seller_url,
      } satisfies Partial<Listing>;
    })
    .catch(() => {
      cache.delete(key);
      return {} as Partial<Listing>;
    });

  cache.set(key, promise);
  const patch = await promise;
  return mergeGalleryIntoListing(listing, patch);
}
