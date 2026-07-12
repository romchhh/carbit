"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { listingSearch, getApiErrorMessage } from "@/lib/api";
import { useAuth } from "@/contexts/AuthProvider";
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
import type { Listing } from "@/types/api";

export function usePreviewSearch(initialFilters: SearchFilterState = { ...DEFAULT_FILTERS }) {
  const { user } = useAuth();
  const resultsRef = useRef<HTMLDivElement>(null);
  const [filters, setFilters] = useState<SearchFilterState>(initialFilters);
  const currencySynced = useRef(false);
  const searchGen = useRef(0);

  useEffect(() => {
    if (!user || currencySynced.current) return;
    currencySynced.current = true;
    const preferred = resolveDisplayCurrency(user.preferred_currency);
    setFilters(prev => {
      if (prev.currency === preferred) return prev;
      const defaults = DEFAULT_PRICE_BY_CURRENCY[preferred];
      return {
        ...prev,
        currency: preferred,
        priceFrom: defaults.from,
        priceTo: defaults.to,
      };
    });
  }, [user]);
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
      const gen = ++searchGen.current;
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
        if (gen !== searchGen.current) return;
        setResults(prev => (append ? [...prev, ...data.items] : data.items));
        setTotal(data.total);
        setPage(data.page);
        setPages(data.pages);
        setFilters({ ...nextFilters });
        setSort(nextSort);
        setFreshness(nextFreshness);
        setRunning(true);
        setError(null);
      } catch (err) {
        if (gen !== searchGen.current) return;
        if (!append) {
          setResults([]);
          setTotal(0);
          setPage(1);
          setPages(0);
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
    const preferred = resolveDisplayCurrency(user?.preferred_currency);
    const defaults = DEFAULT_PRICE_BY_CURRENCY[preferred];
    setFilters({
      ...DEFAULT_FILTERS,
      currency: preferred,
      priceFrom: defaults.from,
      priceTo: defaults.to,
    });
    setResults([]);
    setTotal(0);
    setPage(1);
    setPages(0);
    setSort("newest");
    setFreshness("all");
    setRunning(false);
    setError(null);
  }, [user?.preferred_currency]);

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
