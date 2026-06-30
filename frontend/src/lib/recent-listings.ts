import type { Listing } from "@/types/api";

const KEY = "carbit:recent-listings";
const MAX_ITEMS = 12;

export function loadRecentListings(): Listing[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as Listing[];
    return Array.isArray(parsed) ? parsed : [];
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
