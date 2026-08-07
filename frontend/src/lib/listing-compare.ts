import type { Listing } from "@/types/api";

export const COMPARE_CHANGED_EVENT = "carbit:compare-changed";
export const COMPARE_STORAGE_KEY = "carbit:compare-listings";
export const MAX_COMPARE = 4;

function normalizeListing(raw: unknown): Listing | null {
  if (!raw || typeof raw !== "object") return null;
  const item = raw as Partial<Listing>;
  if (!item.id || typeof item.id !== "string") return null;

  return {
    id: item.id,
    source: item.source ?? "auto_ria",
    title: item.title ?? "Без назви",
    brand: item.brand ?? "",
    model: item.model ?? "",
    year: Number(item.year) || 0,
    price: Number(item.price) || 0,
    currency: item.currency ?? "UAH",
    mileage: Number(item.mileage) || 0,
    fuel: typeof item.fuel === "string" ? item.fuel : "",
    transmission: typeof item.transmission === "string" ? item.transmission : "",
    region: typeof item.region === "string" ? item.region : "",
    engine_volume_l: item.engine_volume_l ?? null,
    description: item.description ?? null,
    images: Array.isArray(item.images)
      ? item.images.filter((url): url is string => typeof url === "string")
      : [],
    url: item.url ?? "",
    seller_type: item.seller_type ?? "private",
    vin: item.vin ?? null,
    vin_checked: item.vin_checked ?? null,
    vin_check_url: item.vin_check_url ?? null,
    source_data: item.source_data ?? null,
    price_history: Array.isArray(item.price_history) ? item.price_history : [],
    is_duplicate: Boolean(item.is_duplicate),
    alternate_sources: Array.isArray(item.alternate_sources)
      ? item.alternate_sources.filter(
          (row): row is NonNullable<Listing["alternate_sources"]>[number] =>
            Boolean(row && typeof row === "object" && typeof row.source === "string" && typeof row.url === "string"),
        )
      : [],
    published_at: item.published_at ?? "",
    refreshed_at: item.refreshed_at ?? null,
    found_at: item.found_at ?? "",
  };
}

function notifyChanged() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(COMPARE_CHANGED_EVENT));
}

export function loadCompareListings(): Listing[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(COMPARE_STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.map(normalizeListing).filter((item): item is Listing => item !== null);
  } catch {
    return [];
  }
}

export function saveCompareListings(listings: Listing[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(COMPARE_STORAGE_KEY, JSON.stringify(listings.slice(0, MAX_COMPARE)));
  notifyChanged();
}

/** Замінити весь список порівняння (напр. з URL або збереженого списку). */
export function replaceCompareListings(listings: Listing[]) {
  saveCompareListings(listings);
}

export function buildCompareShareUrl(listings: Listing[], shareId?: string | null): string {
  if (typeof window === "undefined") return "/app/compare";
  const origin = window.location.origin;
  if (shareId) {
    return `${origin}/app/compare?share=${encodeURIComponent(shareId)}`;
  }
  const ids = listings.map(item => item.id).filter(Boolean);
  if (!ids.length) return `${origin}/app/compare`;
  return `${origin}/app/compare?ids=${encodeURIComponent(ids.join(","))}`;
}

export type CompareAddResult =
  | { ok: true }
  | { ok: false; reason: "full" | "duplicate" };

export function addCompareListing(listing: Listing): CompareAddResult {
  const current = loadCompareListings();
  if (current.some(item => item.id === listing.id)) {
    return { ok: false, reason: "duplicate" };
  }
  if (current.length >= MAX_COMPARE) {
    return { ok: false, reason: "full" };
  }
  saveCompareListings([...current, listing]);
  return { ok: true };
}

export function removeCompareListing(id: string) {
  saveCompareListings(loadCompareListings().filter(item => item.id !== id));
}

export function toggleCompareListing(listing: Listing): CompareAddResult | { ok: true; removed: true } {
  const current = loadCompareListings();
  if (current.some(item => item.id === listing.id)) {
    removeCompareListing(listing.id);
    return { ok: true, removed: true };
  }
  return addCompareListing(listing);
}

export function clearCompareListings() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(COMPARE_STORAGE_KEY);
  notifyChanged();
}

export function isInCompare(id: string): boolean {
  return loadCompareListings().some(item => item.id === id);
}
