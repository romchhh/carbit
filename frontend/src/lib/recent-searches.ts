import { DEFAULT_FILTERS, type SearchFilterState } from "@/lib/search-catalog";
import {
  buildSearchName,
  searchFiltersMatchUi,
  toBackendSearchFilters,
} from "@/lib/search-filters-api";
import type { SearchFreshness } from "@/lib/search-preview";

const KEY = "carbit:recent-searches";
const CHANGED_EVENT = "carbit:recent-searches-changed";
const MAX_ITEMS = 12;

export type RecentSearchEntry = {
  id: string;
  name: string;
  filters: SearchFilterState;
  freshness: SearchFreshness;
  at: string;
};

function normalizeFilters(raw: unknown): SearchFilterState | null {
  if (!raw || typeof raw !== "object") return null;
  return { ...DEFAULT_FILTERS, ...(raw as Partial<SearchFilterState>) };
}

function normalizeEntry(raw: unknown): RecentSearchEntry | null {
  if (!raw || typeof raw !== "object") return null;
  const item = raw as Partial<RecentSearchEntry>;
  const filters = normalizeFilters(item.filters);
  if (!filters) return null;

  const freshness: SearchFreshness = item.freshness === "new" ? "new" : "all";
  const name =
    typeof item.name === "string" && item.name.trim()
      ? item.name.trim()
      : buildSearchName(filters);
  const at =
    typeof item.at === "string" && item.at
      ? item.at
      : new Date().toISOString();
  const id =
    typeof item.id === "string" && item.id
      ? item.id
      : `${at}:${name}:${freshness}`;

  return { id, name, filters, freshness, at };
}

function notifyChanged() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(CHANGED_EVENT));
}

export function loadRecentSearches(): RecentSearchEntry[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map(normalizeEntry)
      .filter((item): item is RecentSearchEntry => item !== null);
  } catch {
    return [];
  }
}

export function saveRecentSearch(
  filters: SearchFilterState,
  freshness: SearchFreshness = "all",
): RecentSearchEntry {
  const entry: RecentSearchEntry = {
    id: `${Date.now()}:${Math.random().toString(36).slice(2, 8)}`,
    name: buildSearchName(filters),
    filters: { ...filters },
    freshness: freshness === "new" ? "new" : "all",
    at: new Date().toISOString(),
  };

  if (typeof window === "undefined") return entry;

  const current = loadRecentSearches().filter(
    item =>
      !(
        searchFiltersMatchUi(toBackendSearchFilters(item.filters), filters) &&
        item.freshness === entry.freshness
      ),
  );
  const next = [entry, ...current].slice(0, MAX_ITEMS);
  localStorage.setItem(KEY, JSON.stringify(next));
  notifyChanged();
  return entry;
}

export function clearRecentSearches() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(KEY);
  notifyChanged();
}

export function recentSearchesChangedEvent() {
  return CHANGED_EVENT;
}
