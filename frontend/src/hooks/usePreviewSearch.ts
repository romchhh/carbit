"use client";

import { startTransition, useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthProvider";
import { listingSearch, fx, getApiErrorMessage } from "@/lib/api";
import { resolveDisplayCurrency } from "@/lib/display-currency";
import {
  DEFAULT_FILTERS,
  normalizePriceRange,
  normalizeYearRange,
  type SearchFilterState,
  type SortOption,
} from "@/lib/search-catalog";
import {
  SEARCH_FIRST_BATCH,
  SEARCH_NEW_WITHIN_DAYS,
  SEARCH_PAGE_SIZE,
  type SearchFreshness,
} from "@/lib/search-preview";
import { toBackendSearchFilters } from "@/lib/search-filters-api";
import type { Listing, SourceStatus } from "@/types/api";

type PageResult = {
  items: Listing[];
  total: number;
  sources?: SourceStatus[];
  partial?: boolean;
  from_cache?: boolean;
};

export function usePreviewSearch(initialFilters: SearchFilterState = { ...DEFAULT_FILTERS }) {
  const { user } = useAuth();
  const resultsRef = useRef<HTMLDivElement>(null);
  const [filters, setFilters] = useState<SearchFilterState>(initialFilters);
  const searchGen = useRef(0);
  const [results, setResults] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [sort, setSort] = useState<SortOption>("newest");
  const [freshness, setFreshness] = useState<SearchFreshness>("new");
  const [running, setRunning] = useState(false);
  const [searching, setSearching] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceStatuses, setSourceStatuses] = useState<SourceStatus[]>([]);
  const [partial, setPartial] = useState(false);
  const [fromCache, setFromCache] = useState(false);
  const loadedCountRef = useRef(0);
  /** Остання валюта з профілю, яку підтягнули у фільтр (щоб не перетирати ручну зміну). */
  const lastSyncedPreferredCurrency = useRef<string | null>(null);

  // Валюта діапазону ціни береться з профілю, але лишається редагованою в фільтрі.
  useEffect(() => {
    if (!user) return;
    const preferred = resolveDisplayCurrency(user.preferred_currency);
    setFilters(prev => {
      const shouldSync =
        lastSyncedPreferredCurrency.current === null ||
        prev.currency === lastSyncedPreferredCurrency.current;
      lastSyncedPreferredCurrency.current = preferred;
      if (!shouldSync || prev.currency === preferred) return prev;
      return { ...prev, currency: preferred };
    });
  }, [user, user?.preferred_currency]);

  const buildRequestFilters = useCallback(
    (nextFilters: SearchFilterState, nextFreshness: SearchFreshness) => {
      const years = normalizeYearRange(nextFilters.yearFrom, nextFilters.yearTo);
      const prices = normalizePriceRange(nextFilters.priceFrom, nextFilters.priceTo);
      const sanitized: SearchFilterState = {
        ...nextFilters,
        yearFrom: years.from,
        yearTo: years.to,
        priceFrom: prices.from,
        priceTo: prices.to,
      };
      const payload = toBackendSearchFilters(sanitized);
      if (nextFreshness === "new") {
        payload.published_within_days = SEARCH_NEW_WITHIN_DAYS;
      }
      return payload;
    },
    [],
  );

  const searchSlice = useCallback(
    async (
      nextFilters: SearchFilterState,
      nextSort: SortOption,
      nextFreshness: SearchFreshness,
      apiPage: number,
    ): Promise<PageResult> => {
      const data = await listingSearch.search(
        buildRequestFilters(nextFilters, nextFreshness),
        apiPage,
        SEARCH_FIRST_BATCH,
        nextSort === "newest" ? "published_desc" : nextSort,
        "preview",
      );
      return {
        items: data.items,
        total: data.total,
        sources: data.sources,
        partial: data.partial,
        from_cache: data.from_cache,
      };
    },
    [buildRequestFilters],
  );

  const syncMeta = (
    data: PageResult,
    nextFilters: SearchFilterState,
    nextSort: SortOption,
    nextFreshness: SearchFreshness,
    loaded: number,
  ) => {
    setTotal(data.total);
    setSourceStatuses(data.sources ?? []);
    setPartial(Boolean(data.partial));
    setFromCache(Boolean(data.from_cache));
    setFilters({ ...nextFilters });
    setSort(nextSort);
    setFreshness(nextFreshness);
    setRunning(true);
    setError(null);
    setPage(Math.max(1, Math.ceil(loaded / SEARCH_PAGE_SIZE)));
    setPages(Math.max(1, Math.ceil(data.total / SEARCH_PAGE_SIZE)));
  };

  const scrollToProgress = useCallback(() => {
    const el = resultsRef.current;
    if (!el) return;
    window.requestAnimationFrame(() => {
      window.setTimeout(() => {
        el.scrollIntoView({ behavior: "smooth", block: "start", inline: "nearest" });
      }, 40);
    });
  }, []);

  const fetchInitial = useCallback(
    async (
      nextFilters: SearchFilterState,
      nextSort: SortOption,
      nextFreshness: SearchFreshness,
    ) => {
      const gen = ++searchGen.current;
      setSearching(true);
      setError(null);
      loadedCountRef.current = 0;
      scrollToProgress();

      try {
        void fx.rates();
        const first = await searchSlice(nextFilters, nextSort, nextFreshness, 1);
        if (gen !== searchGen.current) return;

        loadedCountRef.current = first.items.length;
        startTransition(() => {
          setResults(first.items);
          syncMeta(first, nextFilters, nextSort, nextFreshness, first.items.length);
          setSearching(false);
        });

        if (first.items.length >= SEARCH_FIRST_BATCH && first.total > SEARCH_FIRST_BATCH) {
          const second = await searchSlice(nextFilters, nextSort, nextFreshness, 2);
          if (gen !== searchGen.current) return;
          const merged = [...first.items, ...second.items];
          loadedCountRef.current = merged.length;
          startTransition(() => {
            setResults(merged);
            syncMeta(second, nextFilters, nextSort, nextFreshness, merged.length);
          });
        }
      } catch (err) {
        if (gen !== searchGen.current) return;
        setResults([]);
        setTotal(0);
        setPage(1);
        setPages(0);
        setSourceStatuses([]);
        setPartial(false);
        setFromCache(false);
        setRunning(false);
        loadedCountRef.current = 0;
        setError(getApiErrorMessage(err, "Не вдалось виконати пошук. Спробуйте ще раз."));
      } finally {
        if (gen === searchGen.current) {
          setSearching(false);
          setLoadingMore(false);
        }
      }
    },
    [searchSlice, scrollToProgress],
  );

  const fetchMore = useCallback(
    async (
      nextFilters: SearchFilterState,
      nextSort: SortOption,
      nextFreshness: SearchFreshness,
    ) => {
      const gen = ++searchGen.current;
      setLoadingMore(true);

      try {
        const chunks = Math.ceil(SEARCH_PAGE_SIZE / SEARCH_FIRST_BATCH);
        let startApiPage = Math.floor(loadedCountRef.current / SEARCH_FIRST_BATCH) + 1;
        const collected: Listing[] = [];
        let lastMeta: PageResult | null = null;

        for (let i = 0; i < chunks; i += 1) {
          const data = await searchSlice(nextFilters, nextSort, nextFreshness, startApiPage + i);
          if (gen !== searchGen.current) return;
          lastMeta = data;
          collected.push(...data.items);
          if (data.items.length < SEARCH_FIRST_BATCH) break;
        }

        if (!lastMeta) return;

        startTransition(() => {
          setResults(prev => {
            const seen = new Set(prev.map(item => item.id));
            const unique = collected.filter(item => !seen.has(item.id));
            const merged = [...prev, ...unique];
            loadedCountRef.current = merged.length;
            syncMeta(lastMeta!, nextFilters, nextSort, nextFreshness, merged.length);
            return merged;
          });
        });
      } catch (err) {
        if (gen !== searchGen.current) return;
        setError(getApiErrorMessage(err, "Не вдалось виконати пошук. Спробуйте ще раз."));
      } finally {
        if (gen === searchGen.current) {
          setLoadingMore(false);
        }
      }
    },
    [searchSlice],
  );

  const runSearch = useCallback(
    async (nextFilters: SearchFilterState, nextFreshness: SearchFreshness = freshness) => {
      const years = normalizeYearRange(nextFilters.yearFrom, nextFilters.yearTo);
      const prices = normalizePriceRange(nextFilters.priceFrom, nextFilters.priceTo);
      const sanitized = {
        ...nextFilters,
        yearFrom: years.from,
        yearTo: years.to,
        priceFrom: prices.from,
        priceTo: prices.to,
      };
      setFilters(sanitized);
      await fetchInitial(sanitized, sort, nextFreshness);
    },
    [fetchInitial, freshness, sort],
  );

  const changeSort = useCallback(
    (nextSort: SortOption) => {
      if (!running) {
        setSort(nextSort);
        return;
      }
      void fetchInitial(filters, nextSort, freshness);
    },
    [fetchInitial, filters, freshness, running],
  );

  const changeFreshness = useCallback((nextFreshness: SearchFreshness) => {
    // Лише оновлює режим — пошук стартує тільки по кнопці «Шукати».
    setFreshness(nextFreshness);
  }, []);

  const loadMore = useCallback(() => {
    if (!running || loadingMore || searching) return;
    if (loadedCountRef.current >= total && total > 0) return;
    void fetchMore(filters, sort, freshness);
  }, [fetchMore, filters, freshness, loadingMore, running, searching, sort, total]);

  const reset = useCallback(() => {
    const preferred = resolveDisplayCurrency(user?.preferred_currency);
    lastSyncedPreferredCurrency.current = preferred;
    setFilters({ ...DEFAULT_FILTERS, currency: preferred });
    setResults([]);
    setTotal(0);
    setPage(1);
    setPages(0);
    setSourceStatuses([]);
    setPartial(false);
    setFromCache(false);
    setSort("newest");
    setFreshness("new");
    setRunning(false);
    setError(null);
    loadedCountRef.current = 0;
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
    hasMore: running && results.length < total,
    error,
    sourceStatuses,
    partial,
    fromCache,
    resultsRef,
    runSearch,
    changeSort,
    changeFreshness,
    loadMore,
    reset,
    clearError: () => setError(null),
  };
}
