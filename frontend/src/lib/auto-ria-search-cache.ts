import type { AutoRiaSearchMode } from "@/lib/search-preview";
import type { BackendSearchFilters } from "@/lib/search-filters-api";
import type { PaginatedListings } from "@/types/api";

type SearchParams = {
  filters: BackendSearchFilters;
  page: number;
  perPage: number;
  sortBy: string;
  mode: AutoRiaSearchMode;
};

const CACHE_TTL_MS = 90_000;

const memoryCache = new Map<string, { expires: number; data: PaginatedListings }>();
const inflight = new Map<string, Promise<PaginatedListings>>();

function cacheKey({ filters, page, perPage, sortBy, mode }: SearchParams): string {
  return JSON.stringify({ filters, page, perPage, sortBy, mode });
}

export async function cachedAutoRiaSearch(
  params: SearchParams,
  fetcher: () => Promise<PaginatedListings>,
): Promise<PaginatedListings> {
  const key = cacheKey(params);
  const now = Date.now();

  const cached = memoryCache.get(key);
  if (cached && now < cached.expires) {
    return cached.data;
  }

  const pending = inflight.get(key);
  if (pending) {
    return pending;
  }

  const request = fetcher()
    .then(data => {
      memoryCache.set(key, { expires: Date.now() + CACHE_TTL_MS, data });
      return data;
    })
    .finally(() => {
      inflight.delete(key);
    });

  inflight.set(key, request);
  return request;
}
