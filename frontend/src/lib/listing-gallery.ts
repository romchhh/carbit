import { listings as listingsApi } from "@/lib/api";
import { resolveListingImages } from "@/lib/listing-image-url";
import {
  ensureReonoPhotosDeduped,
  listingNeedsReonoPhotos,
  listingShouldFetchReonoGallery,
} from "@/lib/reono-photos";
import type { Listing } from "@/types/api";

const cache = new Map<string, Promise<Partial<Listing>>>();

const GALLERY_SOURCES = new Set(["auto_ria", "auto_ria_beta", "olx", "imperiya"]);

function cacheKey(listing: Listing): string {
  return `${listing.source}:${listing.id}:${listing.url ?? ""}`;
}

function countValidImages(images: string[] | null | undefined): number {
  return (images ?? []).filter(url => url?.trim()).length;
}

function listingHasBetaIdentity(listing: Listing): boolean {
  if (listing.vin || listing.plate) return true;
  const sourceData = listing.source_data;
  if (!sourceData || typeof sourceData !== "object") return false;
  const vin = typeof sourceData.VIN === "string" ? sourceData.VIN.trim() : "";
  const plate = typeof sourceData.plateNumber === "string" ? sourceData.plateNumber.trim() : "";
  return vin.length === 17 || Boolean(plate);
}

export function listingNeedsGalleryHydration(listing: Listing): boolean {
  const source = (listing.source || "").toLowerCase();
  if (source === "reono") return listingNeedsReonoPhotos(listing);
  if (!GALLERY_SOURCES.has(source)) return false;
  if (!listing.id && !listing.url) return false;
  if (source === "auto_ria_beta" && !listingHasBetaIdentity(listing)) return true;
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
      const patch: Partial<Listing> = {};
      if (images.length) patch.images = images;
      if (result.seller_name) patch.seller_name = result.seller_name;
      if (result.seller_phone) patch.seller_phone = result.seller_phone;
      if (result.seller_telegram) patch.seller_telegram = result.seller_telegram;
      if (result.seller_url) patch.seller_url = result.seller_url;
      if (result.vin) patch.vin = result.vin;
      if (result.plate) patch.plate = result.plate;
      if (result.vin_checked != null) patch.vin_checked = result.vin_checked;
      if (result.vin_check_url) patch.vin_check_url = result.vin_check_url;
      if (result.description) patch.description = result.description;
      if (result.had_accident != null) patch.had_accident = result.had_accident;
      if (result.usa_import != null) patch.usa_import = result.usa_import;
      if (result.engine_volume_l != null) patch.engine_volume_l = result.engine_volume_l;
      if (result.fuel) patch.fuel = result.fuel;
      if (result.transmission) patch.transmission = result.transmission;
      if (result.year) patch.year = result.year;
      if (result.mileage != null) patch.mileage = result.mileage;
      if (result.region) patch.region = result.region;
      if (result.source_data && typeof result.source_data === "object") {
        patch.source_data = {
          ...(listing.source_data ?? {}),
          ...result.source_data,
        };
      }
      if (!Object.keys(patch).length) {
        cache.delete(key);
        return {} as Partial<Listing>;
      }
      return patch;
    })
    .catch(() => {
      cache.delete(key);
      return {} as Partial<Listing>;
    });

  cache.set(key, promise);
  const patch = await promise;
  return mergeGalleryIntoListing(listing, patch);
}
