"use client";

import { startTransition, useCallback, useRef, useState } from "react";
import { listingSearch, fx, getApiErrorMessage } from "@/lib/api";
import {
  DEFAULT_FILTERS,
  DEFAULT_PRICE_BY_CURRENCY,
  type SearchFilterState,
  type SortOption,
} from "@/lib/search-catalog";
import {
  SEARCH_NEW_WITHIN_DAYS,
  SEARCH_PAGE_SIZE,
  type SearchFreshness,
} from "@/lib/search-preview";
import { toBackendSearchFilters } from "@/lib/search-filters-api";
import { resolveDisplayCurrency } from "@/lib/display-currency";
import type { Listing, SourceStatus } from "@/types/api";

export function usePreviewSearch(initialFilters: SearchFilterState = { ...DEFAULT_FILTERS }) {
  const resultsRef = useRef<HTMLDivElement>(null);
  const [filters, setFilters] = useState<SearchFilterState>(initialFilters);
  const searchGen = useRef(0);
  const [results, setResults] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [sort, setSort] = useState<SortOption>("newest");
  const [freshness, setFreshness] = useState<SearchFreshness>("all");
  const [running, setRunning] = useState(false);
  const [searching, setSearching] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceStatuses, setSourceStatuses] = useState<SourceStatus[]>([]);
  const [partial, setPartial] = useState(false);
  const [fromCache, setFromCache] = useState(false);

  const buildRequestFilters = useCallback(
    (nextFilters: SearchFilterState, nextFreshness: SearchFreshness) => {
      const payload = toBackendSearchFilters(nextFilters);
      if (nextFreshness === "new") {
        payload.published_within_days = SEARCH_NEW_WITHIN_DAYS;
      }
      return payload;
    },
    [],
  );

  const fetchPage = useCallback(
    async (
      nextFilters: SearchFilterState,
      nextPage: number,
      nextSort: SortOption,
      nextFreshness: SearchFreshness,
      append: boolean,
    ) => {
      const gen = ++searchGen.current;
      if (append) {
        setLoadingMore(true);
      } else {
        setSearching(true);
        setError(null);
      }

      try {
        void fx.rates();
        const data = await listingSearch.search(
          buildRequestFilters(nextFilters, nextFreshness),
          nextPage,
          SEARCH_PAGE_SIZE,
          nextSort === "newest" ? "published_desc" : nextSort,
          "preview",
        );
        if (gen !== searchGen.current) return;

        startTransition(() => {
          setResults(prev => (append ? [...prev, ...data.items] : data.items));
          setTotal(data.total);
          setPage(data.page);
          setPages(data.pages);
          setSourceStatuses(data.sources ?? []);
          setPartial(Boolean(data.partial));
          setFromCache(Boolean(data.from_cache));
          setFilters({ ...nextFilters });
          setSort(nextSort);
          setFreshness(nextFreshness);
          setRunning(true);
          setError(null);
        });
      } catch (err) {
        if (gen !== searchGen.current) return;
        if (!append) {
          setResults([]);
          setTotal(0);
          setPage(1);
          setPages(0);
          setSourceStatuses([]);
          setPartial(false);
          setFromCache(false);
          setRunning(false);
        }
        setError(getApiErrorMessage(err, "Не вдалось виконати пошук. Спробуйте ще раз."));
      } finally {
        if (gen === searchGen.current) {
          setSearching(false);
          setLoadingMore(false);
        }
      }
    },
    [buildRequestFilters],
  );

  const runSearch = useCallback(
    async (nextFilters: SearchFilterState, nextFreshness: SearchFreshness = freshness) => {
      await fetchPage(nextFilters, 1, sort, nextFreshness, false);
    },
    [fetchPage, freshness, sort],
  );

  const changeSort = useCallback(
    (nextSort: SortOption) => {
      if (!running) {
        setSort(nextSort);
        return;
      }
      void fetchPage(filters, 1, nextSort, freshness, false);
    },
    [fetchPage, filters, freshness, running],
  );

  const changeFreshness = useCallback(
    (nextFreshness: SearchFreshness) => {
      if (!running) {
        setFreshness(nextFreshness);
        return;
      }
      void fetchPage(filters, 1, sort, nextFreshness, false);
    },
    [fetchPage, filters, running, sort],
  );

  const loadMore = useCallback(() => {
    if (!running || loadingMore || searching || page >= pages) return;
    void fetchPage(filters, page + 1, sort, freshness, true);
  }, [fetchPage, filters, freshness, loadingMore, page, pages, running, searching, sort]);

  const reset = useCallback(() => {
    setFilters({
      ...DEFAULT_FILTERS,
      currency: "USD",
      priceFrom: DEFAULT_PRICE_BY_CURRENCY.USD.from,
      priceTo: DEFAULT_PRICE_BY_CURRENCY.USD.to,
    });
    setResults([]);
    setTotal(0);
    setPage(1);
    setPages(0);
    setSourceStatuses([]);
    setPartial(false);
    setFromCache(false);
    setSort("newest");
    setFreshness("all");
    setRunning(false);
    setError(null);
  }, []);

  return {
    filters,
    setFilters,
    results,
    total,
    page,
    pages,
    sort,
    freshness,
    running,
    searching,
    loadingMore,
    hasMore: running && page < pages,
    error,
    sourceStatuses,
    partial,
    fromCache,
    displayCurrency: resolveDisplayCurrency(filters.currency),
    resultsRef,
    runSearch,
    changeSort,
    changeFreshness,
    loadMore,
    reset,
    clearError: () => setError(null),
  };
}
