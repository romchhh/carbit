const KEY = "carbit:viewed-listings";
export const VIEWED_LISTINGS_CHANGED_EVENT = "carbit:viewed-listings-changed";
const MAX_IDS = 300;

function notifyChanged() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(VIEWED_LISTINGS_CHANGED_EVENT));
}

function readIds(): string[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((id): id is string => typeof id === "string" && id.length > 0);
  } catch {
    return [];
  }
}

function writeIds(ids: string[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(KEY, JSON.stringify(ids.slice(0, MAX_IDS)));
    notifyChanged();
  } catch {
    /* ignore quota */
  }
}

export function loadViewedListingIds(): Set<string> {
  return new Set(readIds());
}

export function isListingViewed(listingId: string): boolean {
  if (!listingId) return false;
  return loadViewedListingIds().has(listingId);
}

export function markListingViewed(listingId: string): void {
  if (!listingId || typeof window === "undefined") return;
  const next = [listingId, ...readIds().filter(id => id !== listingId)].slice(0, MAX_IDS);
  writeIds(next);
}

export function clearViewedListings(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(KEY);
  notifyChanged();
}
