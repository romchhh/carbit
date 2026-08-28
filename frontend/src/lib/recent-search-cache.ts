import type { SortOption } from "@/lib/search-catalog";
import type { SearchFilterState } from "@/lib/search-catalog";
import type { SearchFreshness } from "@/lib/search-preview";
import {
  loadRecentSearches,
  saveRecentSearch,
  updateRecentSearchCache,
  type RecentSearchEntry,
} from "@/lib/recent-searches";
import {
  searchFiltersMatchUi,
  toBackendSearchFilters,
} from "@/lib/search-filters-api";
import type { Listing } from "@/types/api";

export const RECENT_CACHE_TTL_MS = 24 * 60 * 60 * 1000;
export const RECENT_CACHE_REFRESH_MS = 5 * 60 * 1000;
/** Скільки карток зберігаємо на один пошук (≈2 сторінки). */
export const RECENT_CACHE_MAX_LISTINGS = 40;

export type RecentSearchResultCache = {
  results: Listing[];
  total: number;
  marketTotal: number | null;
  sort: SortOption;
  pages: number;
  cachedAt: string;
};

function slimListing(item: Listing): Listing {
  return {
    ...item,
    description: null,
    source_data: null,
    price_history: [],
    seller_phone: null,
    seller_telegram: null,
  };
}

export function buildRecentSearchCache(
  results: Listing[],
  total: number,
  marketTotal: number | null,
  sort: SortOption,
  pages: number,
): RecentSearchResultCache {
  return {
    results: results.slice(0, RECENT_CACHE_MAX_LISTINGS).map(slimListing),
    total,
    marketTotal,
    sort,
    pages,
    cachedAt: new Date().toISOString(),
  };
}

export function isRecentCacheFresh(cache: RecentSearchResultCache): boolean {
  const at = Date.parse(cache.cachedAt);
  if (!Number.isFinite(at)) return false;
  return Date.now() - at <= RECENT_CACHE_TTL_MS;
}

export function shouldRefreshRecentCache(cache: RecentSearchResultCache): boolean {
  const at = Date.parse(cache.cachedAt);
  if (!Number.isFinite(at)) return true;
  return Date.now() - at > RECENT_CACHE_REFRESH_MS;
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

export function findRecentSearchCache(
  filters: SearchFilterState,
  freshness: SearchFreshness,
): RecentSearchResultCache | null {
  const entry = loadRecentSearches().find(item => matchesEntry(item, filters, freshness));
  if (!entry?.cache || !isRecentCacheFresh(entry.cache)) return null;
  return entry.cache;
}

/** Зберігає результати пошуку в localStorage (останні 5 запитів). */
export function persistRecentSearchCache(
  filters: SearchFilterState,
  freshness: SearchFreshness,
  data: {
    results: Listing[];
    total: number;
    marketTotal: number | null;
    sort: SortOption;
    pages: number;
  },
): void {
  if (typeof window === "undefined" || data.results.length === 0) return;
  const freshnessNorm: SearchFreshness = freshness === "new" ? "new" : "all";
  const hasEntry = loadRecentSearches().some(item => matchesEntry(item, filters, freshnessNorm));
  if (!hasEntry) {
    saveRecentSearch(filters, freshnessNorm);
  }
  const previewImage = data.results.find(item => item.images?.[0])?.images?.[0] ?? null;
  updateRecentSearchCache(
    filters,
    freshnessNorm,
    buildRecentSearchCache(
      data.results,
      data.total,
      data.marketTotal,
      data.sort,
      data.pages,
    ),
    previewImage,
  );
}
