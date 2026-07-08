"use client";

import { useCallback, useRef, useState } from "react";
import { listingSearch, getApiErrorMessage } from "@/lib/api";
import { DEFAULT_FILTERS, type SearchFilterState, type SortOption } from "@/lib/search-catalog";
import {
  SEARCH_NEW_WITHIN_DAYS,
  SEARCH_PAGE_SIZE,
  type SearchFreshness,
} from "@/lib/search-preview";
import { toBackendSearchFilters } from "@/lib/search-filters-api";
import type { Listing } from "@/types/api";

export function usePreviewSearch(initialFilters: SearchFilterState = { ...DEFAULT_FILTERS }) {
  const resultsRef = useRef<HTMLDivElement>(null);
  const [filters, setFilters] = useState<SearchFilterState>(initialFilters);
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
      if (append) {
        setLoadingMore(true);
      } else {
        setSearching(true);
        setError(null);
        requestAnimationFrame(() => {
          resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      }

      try {
        const data = await listingSearch.search(
          buildRequestFilters(nextFilters, nextFreshness),
          nextPage,
          SEARCH_PAGE_SIZE,
          nextSort === "newest" ? "published_desc" : nextSort,
          "preview",
        );
        setResults(prev => (append ? [...prev, ...data.items] : data.items));
        setTotal(data.total);
        setPage(data.page);
        setPages(data.pages);
        setFilters({ ...nextFilters });
        setSort(nextSort);
        setFreshness(nextFreshness);
        setRunning(true);
      } catch (err) {
        if (!append) {
          setResults([]);
          setTotal(0);
          setPage(1);
          setPages(0);
          setRunning(false);
        }
        setError(getApiErrorMessage(err, "Не вдалось виконати пошук. Спробуйте ще раз."));
      } finally {
        setSearching(false);
        setLoadingMore(false);
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
    setFilters({ ...DEFAULT_FILTERS });
    setResults([]);
    setTotal(0);
    setPage(1);
    setPages(0);
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
    resultsRef,
    runSearch,
    changeSort,
    changeFreshness,
    loadMore,
    reset,
    clearError: () => setError(null),
  };
}
