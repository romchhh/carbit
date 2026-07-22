"use client";

import { startTransition, useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthProvider";
import { listingSearch, fx, getApiErrorMessage, isSearchRateLimitError, ApiError } from "@/lib/api";
import { resolveDisplayCurrency } from "@/lib/display-currency";
import {
  DEFAULT_FILTERS,
  normalizePriceRange,
  normalizeYearRange,
  type SearchFilterState,
  type SortOption,
  sortListingItems,
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
  marketTotal?: number | null;
  sources?: SourceStatus[];
  partial?: boolean;
  from_cache?: boolean;
};

function mergeUniquePool(pool: Listing[], items: Listing[]): Listing[] {
  if (items.length === 0) return pool;
  const seen = new Set(pool.map(item => item.id));
  const next = [...pool];
  for (const item of items) {
    if (seen.has(item.id)) continue;
    seen.add(item.id);
    next.push(item);
  }
  return next;
}

export function usePreviewSearch(initialFilters: SearchFilterState = { ...DEFAULT_FILTERS }) {
  const { user } = useAuth();
  const resultsRef = useRef<HTMLDivElement>(null);
  const [filters, setFilters] = useState<SearchFilterState>(initialFilters);
  const searchGen = useRef(0);
  const [results, setResults] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [marketTotal, setMarketTotal] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [sort, setSort] = useState<SortOption>("newest");
  const [freshness, setFreshness] = useState<SearchFreshness>("all");
  const [running, setRunning] = useState(false);
  const [searching, setSearching] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorRetryAfter, setErrorRetryAfter] = useState<number | null>(null);
  const [sourceStatuses, setSourceStatuses] = useState<SourceStatus[]>([]);
  const [partial, setPartial] = useState(false);
  const [fromCache, setFromCache] = useState(false);
  /** Усі оголошення з live-пулу (підвантажуються з кешу бекенду, без нового OLX-скану). */
  const fullPoolRef = useRef<Listing[]>([]);
  /** Скільки карток показуємо з відсортованого пулу. */
  const displayCountRef = useRef(0);
  /** sort, з яким будувався Redis-пул (сторінки 2+ мають той самий sort_by). */
  const poolApiSortRef = useRef<SortOption>("newest");
  const hydratingPoolRef = useRef(false);
  const lastSyncedPreferredCurrency = useRef<string | null>(null);

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
      apiSort: SortOption,
      nextFreshness: SearchFreshness,
      apiPage: number,
    ): Promise<PageResult> => {
      const data = await listingSearch.search(
        buildRequestFilters(nextFilters, nextFreshness),
        apiPage,
        SEARCH_FIRST_BATCH,
        apiSort === "newest" ? "published_desc" : apiSort,
        "preview",
      );
      return {
        items: data.items,
        total: data.total,
        marketTotal: data.market_total,
        sources: data.sources,
        partial: data.partial,
        from_cache: data.from_cache,
      };
    },
    [buildRequestFilters],
  );

  const applyView = useCallback((sortKey: SortOption, displayCount: number) => {
    const sorted = sortListingItems(fullPoolRef.current, sortKey);
    const count = Math.min(Math.max(displayCount, 0), sorted.length);
    displayCountRef.current = count;
    setResults(sorted.slice(0, count));
    setPage(Math.max(1, Math.ceil(count / SEARCH_PAGE_SIZE)));
  }, []);

  const syncMeta = (
    data: PageResult,
    nextFilters: SearchFilterState,
    nextSort: SortOption,
    nextFreshness: SearchFreshness,
  ) => {
    setTotal(data.total);
    setMarketTotal(data.marketTotal ?? null);
    setSourceStatuses(data.sources ?? []);
    setPartial(Boolean(data.partial));
    setFromCache(Boolean(data.from_cache));
    setFilters({ ...nextFilters });
    setSort(nextSort);
    setFreshness(nextFreshness);
    setRunning(true);
    setError(null);
    setErrorRetryAfter(null);
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

  const hydrateFullPool = useCallback(
    async (
      gen: number,
      nextFilters: SearchFilterState,
      nextFreshness: SearchFreshness,
      targetTotal: number,
      viewSort: SortOption,
    ) => {
      if (hydratingPoolRef.current || targetTotal <= 0) return;
      if (fullPoolRef.current.length >= targetTotal) return;

      hydratingPoolRef.current = true;
      const apiSort = poolApiSortRef.current;
      try {
        let apiPage = Math.floor(fullPoolRef.current.length / SEARCH_FIRST_BATCH) + 1;
        const maxApiPage = Math.ceil(targetTotal / SEARCH_FIRST_BATCH) + 2;

        while (
          gen === searchGen.current &&
          fullPoolRef.current.length < targetTotal &&
          apiPage <= maxApiPage
        ) {
          const data = await searchSlice(nextFilters, apiSort, nextFreshness, apiPage);
          if (gen !== searchGen.current) return;

          fullPoolRef.current = mergeUniquePool(fullPoolRef.current, data.items);
          if (data.items.length < SEARCH_FIRST_BATCH) break;
          apiPage += 1;
        }

        if (gen === searchGen.current) {
          startTransition(() => {
            applyView(viewSort, displayCountRef.current);
          });
        }
      } catch {
        /* фонове дозавантаження — не ламаємо UI */
      } finally {
        hydratingPoolRef.current = false;
      }
    },
    [applyView, searchSlice],
  );

  const fetchInitial = useCallback(
    async (
      nextFilters: SearchFilterState,
      nextSort: SortOption,
      nextFreshness: SearchFreshness,
    ) => {
      const gen = ++searchGen.current;
      setSearching(true);
      setError(null);
      setErrorRetryAfter(null);
      fullPoolRef.current = [];
      displayCountRef.current = 0;
      poolApiSortRef.current = nextSort;
      scrollToProgress();

      try {
        void fx.rates();
        const first = await searchSlice(nextFilters, nextSort, nextFreshness, 1);
        if (gen !== searchGen.current) return;

        fullPoolRef.current = [...first.items];
        displayCountRef.current = first.items.length;

        startTransition(() => {
          applyView(nextSort, displayCountRef.current);
          syncMeta(first, nextFilters, nextSort, nextFreshness);
          setSearching(false);
        });

        if (first.items.length >= SEARCH_FIRST_BATCH && first.total > SEARCH_FIRST_BATCH) {
          const second = await searchSlice(nextFilters, nextSort, nextFreshness, 2);
          if (gen !== searchGen.current) return;
          fullPoolRef.current = mergeUniquePool(fullPoolRef.current, second.items);
          displayCountRef.current = fullPoolRef.current.length;
          startTransition(() => {
            applyView(nextSort, displayCountRef.current);
            syncMeta(second, nextFilters, nextSort, nextFreshness);
          });
        }

        void hydrateFullPool(gen, nextFilters, nextFreshness, first.total, nextSort);
      } catch (err) {
        if (gen !== searchGen.current) return;
        fullPoolRef.current = [];
        displayCountRef.current = 0;
        setResults([]);
        setTotal(0);
        setPage(1);
        setPages(0);
        setSourceStatuses([]);
        setPartial(false);
        setFromCache(false);
        setRunning(false);
        setError(getApiErrorMessage(err, "Не вдалось виконати пошук. Спробуйте ще раз."));
        if (isSearchRateLimitError(err) && err instanceof ApiError) {
          setErrorRetryAfter(err.retryAfter ?? 3600);
        } else {
          setErrorRetryAfter(null);
        }
      } finally {
        if (gen === searchGen.current) {
          setSearching(false);
          setLoadingMore(false);
        }
      }
    },
    [applyView, hydrateFullPool, scrollToProgress, searchSlice],
  );

  const fetchMoreFromServer = useCallback(
    async (
      gen: number,
      nextFilters: SearchFilterState,
      nextFreshness: SearchFreshness,
      viewSort: SortOption,
      targetDisplay: number,
    ) => {
      const apiSort = poolApiSortRef.current;
      let apiPage = Math.floor(fullPoolRef.current.length / SEARCH_FIRST_BATCH) + 1;
      let lastMeta: PageResult | null = null;

      for (let attempt = 0; attempt < 4; attempt += 1) {
        if (fullPoolRef.current.length >= targetDisplay) break;
        const data = await searchSlice(nextFilters, apiSort, nextFreshness, apiPage);
        if (gen !== searchGen.current) return;
        lastMeta = data;
        fullPoolRef.current = mergeUniquePool(fullPoolRef.current, data.items);
        if (data.items.length < SEARCH_FIRST_BATCH) break;
        apiPage += 1;
      }

      if (gen !== searchGen.current) return;

      startTransition(() => {
        applyView(viewSort, targetDisplay);
        if (lastMeta) {
          syncMeta(lastMeta, nextFilters, viewSort, nextFreshness);
        }
      });
    },
    [applyView, searchSlice],
  );

  const loadMore = useCallback(() => {
    if (!running || loadingMore || searching) return;
    if (displayCountRef.current >= total && total > 0) return;

    const gen = searchGen.current;
    const targetDisplay = displayCountRef.current + SEARCH_PAGE_SIZE;

    if (fullPoolRef.current.length >= targetDisplay) {
      applyView(sort, targetDisplay);
      return;
    }

    if (fullPoolRef.current.length >= total) {
      applyView(sort, Math.min(targetDisplay, fullPoolRef.current.length));
      return;
    }

    setLoadingMore(true);
    void fetchMoreFromServer(gen, filters, freshness, sort, targetDisplay).finally(() => {
      if (gen === searchGen.current) setLoadingMore(false);
    });
  }, [
    applyView,
    fetchMoreFromServer,
    filters,
    freshness,
    loadingMore,
    running,
    searching,
    sort,
    total,
  ]);

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
      setSort(nextSort);
      if (!running || fullPoolRef.current.length === 0) return;
      startTransition(() => {
        applyView(nextSort, displayCountRef.current);
      });
    },
    [applyView, running],
  );

  const changeFreshness = useCallback((nextFreshness: SearchFreshness) => {
    setFreshness(nextFreshness);
  }, []);

  const reset = useCallback(() => {
    const preferred = resolveDisplayCurrency(user?.preferred_currency);
    lastSyncedPreferredCurrency.current = preferred;
    setFilters({ ...DEFAULT_FILTERS, currency: preferred });
    fullPoolRef.current = [];
    displayCountRef.current = 0;
    setResults([]);
    setTotal(0);
    setMarketTotal(null);
    setPage(1);
    setPages(0);
    setSourceStatuses([]);
    setPartial(false);
    setFromCache(false);
    setSort("newest");
    setFreshness("new");
    setRunning(false);
    setError(null);
    setErrorRetryAfter(null);
  }, [user?.preferred_currency]);

  return {
    filters,
    setFilters,
    results,
    total,
    marketTotal,
    page,
    pages,
    sort,
    freshness,
    running,
    searching,
    loadingMore,
    hasMore: running && results.length < total,
    error,
    errorRetryAfter,
    sourceStatuses,
    partial,
    fromCache,
    resultsRef,
    runSearch,
    changeSort,
    changeFreshness,
    loadMore,
    reset,
    clearError: () => {
      setError(null);
      setErrorRetryAfter(null);
    },
  };
}
