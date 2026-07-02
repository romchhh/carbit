import type { Listing } from "@/types/api";

const KEY = "carbit:recent-listings";
const MAX_ITEMS = 12;

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
    published_at: item.published_at ?? "",
    found_at: item.found_at ?? "",
  };
}

export function loadRecentListings(): Listing[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.map(normalizeListing).filter((item): item is Listing => item !== null);
  } catch {
    return [];
  }
}

export function saveRecentListing(listing: Listing) {
  if (typeof window === "undefined") return;
  const current = loadRecentListings().filter(item => item.id !== listing.id);
  const next = [listing, ...current].slice(0, MAX_ITEMS);
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent("carbit:recent-listings-changed"));
}

export function clearRecentListings() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(KEY);
  window.dispatchEvent(new CustomEvent("carbit:recent-listings-changed"));
}
