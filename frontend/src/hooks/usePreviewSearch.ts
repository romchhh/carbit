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

/** Додає унікальні картки і тримає обране сортування всього пулу. */
function mergePoolSorted(pool: Listing[], incoming: Listing[], sortKey: SortOption): Listing[] {
  return sortListingItems(appendUniqueToPool(pool, incoming), sortKey);
}

/** Пул: нові (з API) — в кінець, без дублів. */
function appendUniqueToPool(pool: Listing[], incoming: Listing[]): Listing[] {
  if (incoming.length === 0) return pool;
  const seen = new Set(pool.map(item => item.id));
  const appended = [...pool];
  for (const item of incoming) {
    if (seen.has(item.id)) continue;
    seen.add(item.id);
    appended.push(item);
  }
  return appended;
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

  /**
   * fullPoolRef — весь пул у ПОРЯДКУ ОТРИМАННЯ з API (не пересортований).
   * Для сортування "price_asc" тощо — сортуємо display-зріз окремо.
   */
  const fullPoolRef = useRef<Listing[]>([]);
  /**
   * displayPoolRef — лише той порядок, що вже показаний користувачеві.
   * "Показати ще" — append нових в кінець, без пересортування вже показаних.
   */
  const displayPoolRef = useRef<Listing[]>([]);
  const displayCountRef = useRef(0);
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
        apiSort,
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

  /**
   * Показати count карток із displayPoolRef.
   * Якщо count > displayPool — домальовуємо з fullPool (у порядку отримання).
   * Ніколи не пересортовуємо вже показані картки.
   */
  const applyDisplaySlice = useCallback((count: number) => {
    const full = fullPoolRef.current;
    const clamped = Math.min(Math.max(count, 0), full.length);
    displayPoolRef.current = full.slice(0, clamped);
    displayCountRef.current = clamped;
    setResults([...displayPoolRef.current]);
    setPage(Math.max(1, Math.ceil(clamped / SEARCH_PAGE_SIZE)));
  }, []);

  /**
   * Для зміни сортування: пересортовуємо весь fullPool і замінюємо displayPool.
   * Викликається лише при явній зміні sort-опції користувачем.
   */
  const applySortedView = useCallback((sortKey: SortOption, count: number) => {
    const sorted = sortListingItems(fullPoolRef.current, sortKey);
    const clamped = Math.min(Math.max(count, 0), sorted.length);
    displayPoolRef.current = sorted.slice(0, clamped);
    displayCountRef.current = clamped;
    setResults([...displayPoolRef.current]);
    setPage(Math.max(1, Math.ceil(clamped / SEARCH_PAGE_SIZE)));
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

  /** Фонове дозавантаження — тихо наповнює fullPool без зміни displayPool. */
  const hydrateFullPool = useCallback(
    async (
      gen: number,
      nextFilters: SearchFilterState,
      nextFreshness: SearchFreshness,
      targetTotal: number,
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
          fullPoolRef.current = mergePoolSorted(fullPoolRef.current, data.items, apiSort);
          if (data.items.length < SEARCH_FIRST_BATCH) break;
          apiPage += 1;
        }
        // НЕ оновлюємо display — щоб фон не пересортував показані картки
      } catch {
        /* фонове дозавантаження — не ламаємо UI */
      } finally {
        hydratingPoolRef.current = false;
      }
    },
    [searchSlice],
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
      displayPoolRef.current = [];
      displayCountRef.current = 0;
      poolApiSortRef.current = nextSort;
      scrollToProgress();

      try {
        void fx.rates();
        const first = await searchSlice(nextFilters, nextSort, nextFreshness, 1);
        if (gen !== searchGen.current) return;

        // Перший пакет сортуємо (тут ще немає показаних карток, тому безпечно)
        const firstSorted = sortListingItems(first.items, nextSort);
        fullPoolRef.current = [...firstSorted];
        displayPoolRef.current = [...firstSorted];
        displayCountRef.current = firstSorted.length;

        startTransition(() => {
          setResults([...firstSorted]);
          setPage(Math.max(1, Math.ceil(firstSorted.length / SEARCH_PAGE_SIZE)));
          syncMeta(first, nextFilters, nextSort, nextFreshness);
          setSearching(false);
        });

        if (first.items.length >= SEARCH_FIRST_BATCH && first.total > SEARCH_FIRST_BATCH) {
          const second = await searchSlice(nextFilters, nextSort, nextFreshness, 2);
          if (gen !== searchGen.current) return;
          // Другий пакет — append нових в кінець fullPool і displayPool
          fullPoolRef.current = mergePoolSorted(fullPoolRef.current, second.items, nextSort);
          const newCount = fullPoolRef.current.length;
          displayPoolRef.current = fullPoolRef.current.slice(0, newCount);
          displayCountRef.current = newCount;
          startTransition(() => {
            setResults([...displayPoolRef.current]);
            setPage(Math.max(1, Math.ceil(newCount / SEARCH_PAGE_SIZE)));
            syncMeta(second, nextFilters, nextSort, nextFreshness);
          });
        }

        void hydrateFullPool(gen, nextFilters, nextFreshness, first.total);
      } catch (err) {
        if (gen !== searchGen.current) return;
        fullPoolRef.current = [];
        displayPoolRef.current = [];
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
    [hydrateFullPool, scrollToProgress, searchSlice],
  );

  const fetchMoreFromServer = useCallback(
    async (
      gen: number,
      nextFilters: SearchFilterState,
      nextFreshness: SearchFreshness,
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
        fullPoolRef.current = mergePoolSorted(fullPoolRef.current, data.items, apiSort);
        if (data.items.length < SEARCH_FIRST_BATCH) break;
        apiPage += 1;
      }

      if (gen !== searchGen.current) return;

      startTransition(() => {
        // append нових в кінець displayPool, без пересортування вже показаних
        applyDisplaySlice(targetDisplay);
        if (lastMeta) {
          const { sources, partial: p, from_cache: fc, total: t, marketTotal: mt } = {
            sources: lastMeta.sources,
            partial: lastMeta.partial,
            from_cache: lastMeta.from_cache,
            total: lastMeta.total,
            marketTotal: lastMeta.marketTotal,
          };
          setSourceStatuses(sources ?? []);
          setPartial(Boolean(p));
          setFromCache(Boolean(fc));
          setTotal(t);
          setMarketTotal(mt ?? null);
          setPages(Math.max(1, Math.ceil(t / SEARCH_PAGE_SIZE)));
        }
      });
    },
    [applyDisplaySlice, searchSlice],
  );

  const loadMore = useCallback(() => {
    if (!running || loadingMore || searching) return;
    if (displayCountRef.current >= total && total > 0) return;

    const gen = searchGen.current;
    const targetDisplay = displayCountRef.current + SEARCH_PAGE_SIZE;

    // Вже є в fullPool — просто додаємо в кінець display
    if (fullPoolRef.current.length >= targetDisplay) {
      applyDisplaySlice(targetDisplay);
      return;
    }

    if (fullPoolRef.current.length >= total) {
      applyDisplaySlice(Math.min(targetDisplay, fullPoolRef.current.length));
      return;
    }

    setLoadingMore(true);
    void fetchMoreFromServer(gen, filters, freshness, targetDisplay).finally(() => {
      if (gen === searchGen.current) setLoadingMore(false);
    });
  }, [
    applyDisplaySlice,
    fetchMoreFromServer,
    filters,
    freshness,
    loadingMore,
    running,
    searching,
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
      // При явній зміні сортування — пересортовуємо весь пул і показуємо спочатку
      startTransition(() => {
        applySortedView(nextSort, displayCountRef.current);
      });
    },
    [applySortedView, running],
  );

  const changeFreshness = useCallback((nextFreshness: SearchFreshness) => {
    setFreshness(nextFreshness);
  }, []);

  const reset = useCallback(() => {
    const preferred = resolveDisplayCurrency(user?.preferred_currency);
    lastSyncedPreferredCurrency.current = preferred;
    setFilters({ ...DEFAULT_FILTERS, currency: preferred });
    fullPoolRef.current = [];
    displayPoolRef.current = [];
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
