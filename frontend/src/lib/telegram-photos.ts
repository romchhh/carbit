import { listings as listingsApi } from "@/lib/api";
import type { Listing } from "@/types/api";

const inflight = new Map<string, Promise<Listing>>();

/** Telethon лежить на весь бекенд, тож немає сенсу питати по кожній картці. */
const UNAVAILABLE_TTL_MS = 60_000;
let unavailableUntil = 0;

export function telegramPhotosUnavailable(): boolean {
  return Date.now() < unavailableUntil;
}

export function noteTelegramPhotosState(listing: Listing | null | undefined): void {
  if (listing?.source_data?.photos_unavailable) {
    unavailableUntil = Date.now() + UNAVAILABLE_TTL_MS;
  } else if (listing?.images?.length) {
    unavailableUntil = 0;
  }
}

/** Один запит на оголошення, скільки б карток його одночасно не просило. */
export function ensurePhotosDeduped(id: string): Promise<Listing> {
  let pending = inflight.get(id);
  if (!pending) {
    pending = listingsApi
      .ensurePhotos(id)
      .then(fresh => {
        noteTelegramPhotosState(fresh);
        return fresh;
      })
      .finally(() => {
        inflight.delete(id);
      });
    inflight.set(id, pending);
  }
  return pending;
}
