import { DEFAULT_FILTERS, type SearchFilterState } from "@/lib/search-catalog";
import {
  buildSearchName,
  searchFiltersMatchUi,
  toBackendSearchFilters,
} from "@/lib/search-filters-api";
import { syncSearchFilterArrays } from "@/lib/search-filter-multi";
import type { RecentSearchResultCache } from "@/lib/recent-search-cache";
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
  /** Фото першого авто з останнього запуску цього пошуку */
  previewImage?: string | null;
  /** Кеш результатів для миттєвого відкриття */
  cache?: RecentSearchResultCache;
};

function normalizeFilters(raw: unknown): SearchFilterState | null {
  if (!raw || typeof raw !== "object") return null;
  return syncSearchFilterArrays({ ...DEFAULT_FILTERS, ...(raw as Partial<SearchFilterState>) });
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
  const previewImage =
    typeof item.previewImage === "string" && item.previewImage.trim()
      ? item.previewImage.trim()
      : null;
  const cache =
    item.cache &&
    typeof item.cache === "object" &&
    Array.isArray((item.cache as RecentSearchResultCache).results)
      ? (item.cache as RecentSearchResultCache)
      : undefined;

  return { id, name, filters, freshness, at, previewImage, cache };
}

function notifyChanged() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(CHANGED_EVENT));
}

function matchesEntry(
  item: RecentSearchEntry,
  filters: SearchFilterState,
  freshness: SearchFreshness,
): boolean {
  return (
    searchFiltersMatchUi(toBackendSearchFilters(item.filters), filters) &&
    item.freshness === freshness
  );
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

export type SaveRecentSearchOptions = {
  previewImage?: string | null;
};

export function saveRecentSearch(
  filters: SearchFilterState,
  freshness: SearchFreshness = "all",
  options?: SaveRecentSearchOptions,
): RecentSearchEntry {
  const freshnessNorm: SearchFreshness = freshness === "new" ? "new" : "all";
  const current = typeof window === "undefined" ? [] : loadRecentSearches();
  const previous = current.find(item => matchesEntry(item, filters, freshnessNorm));
  const previewImage =
    options && "previewImage" in options
      ? options.previewImage?.trim() || null
      : previous?.previewImage ?? null;

  const entry: RecentSearchEntry = {
    id: `${Date.now()}:${Math.random().toString(36).slice(2, 8)}`,
    name: buildSearchName(filters),
    filters: { ...filters },
    freshness: freshnessNorm,
    at: new Date().toISOString(),
    previewImage,
    cache: previous?.cache,
  };

  if (typeof window === "undefined") return entry;

  const next = [entry, ...current.filter(item => !matchesEntry(item, filters, freshnessNorm))].slice(
    0,
    MAX_ITEMS,
  );
  localStorage.setItem(KEY, JSON.stringify(next));
  notifyChanged();
  return entry;
}

export function updateRecentSearchCache(
  filters: SearchFilterState,
  freshness: SearchFreshness,
  cache: RecentSearchResultCache,
  previewImage?: string | null,
): void {
  if (typeof window === "undefined") return;
  const freshnessNorm: SearchFreshness = freshness === "new" ? "new" : "all";
  const current = loadRecentSearches();
  const idx = current.findIndex(item => matchesEntry(item, filters, freshnessNorm));
  if (idx < 0) return;

  const prev = current[idx];
  const nextEntry: RecentSearchEntry = {
    ...prev,
    previewImage:
      previewImage?.trim() || prev.previewImage || cache.results[0]?.images?.[0] || null,
    cache,
    at: new Date().toISOString(),
  };
  const next = [...current];
  next[idx] = nextEntry;
  localStorage.setItem(KEY, JSON.stringify(next));
  notifyChanged();
}

export function clearRecentSearches() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(KEY);
  notifyChanged();
}

export function recentSearchesChangedEvent() {
  return CHANGED_EVENT;
}
