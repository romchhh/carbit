import type { SearchFilterState } from "@/lib/search-catalog";

const KEY = "carbit:search-draft";

export function saveSearchDraft(filters: SearchFilterState) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(KEY, JSON.stringify(filters));
}

export function loadSearchDraft(): SearchFilterState | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SearchFilterState;
  } catch {
    return null;
  }
}

export function clearSearchDraft() {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(KEY);
}
