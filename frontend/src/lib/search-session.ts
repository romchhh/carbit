import type { SearchFilterState, SortOption } from "@/lib/search-catalog";
import type { SearchFreshness } from "@/lib/search-preview";
import type { Listing, SourceStatus } from "@/types/api";

const KEY = "carbit:search-session";
const MAX_AGE_MS = 24 * 60 * 60 * 1000;
const MAX_STORED_RESULTS = 48;

export type SearchSessionSnapshot = {
  filters: SearchFilterState;
  freshness: SearchFreshness;
  sort: SortOption;
  running: boolean;
  results: Listing[];
  total: number;
  marketTotal: number | null;
  page: number;
  pages: number;
  poolSize: number;
  loadedApiPage: number;
  sourceStatuses: SourceStatus[];
  partial: boolean;
  fromCache: boolean;
  savedAt: number;
};

function trimResults(items: Listing[]): Listing[] {
  return items.slice(0, MAX_STORED_RESULTS);
}

export function saveSearchSession(snapshot: SearchSessionSnapshot): void {
  if (typeof window === "undefined" || !snapshot.running) return;
  try {
    const payload: SearchSessionSnapshot = {
      ...snapshot,
      results: trimResults(snapshot.results),
      savedAt: Date.now(),
    };
    sessionStorage.setItem(KEY, JSON.stringify(payload));
  } catch {
    /* quota or private mode */
  }
}

export function loadSearchSession(): SearchSessionSnapshot | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as SearchSessionSnapshot;
    if (!parsed?.running || !Array.isArray(parsed.results)) return null;
    if (Date.now() - (parsed.savedAt || 0) > MAX_AGE_MS) {
      sessionStorage.removeItem(KEY);
      return null;
    }
    return {
      ...parsed,
      results: trimResults(parsed.results),
    };
  } catch {
    return null;
  }
}

export function clearSearchSession(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(KEY);
}
