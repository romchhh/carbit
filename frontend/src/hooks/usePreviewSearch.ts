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
import { clearSearchSession, type SearchSessionSnapshot } from "@/lib/search-session";
import type { RecentSearchResultCache } from "@/lib/recent-search-cache";
import type { Listing, SourceStatus } from "@/types/api";

type RunSearchOptions = {
  /** Оновити результати без очищення поточного екрану (для кешу недавніх пошуків). */
  background?: boolean;
};

type PageResult = {
  items: Listing[];
  total: number;
  pages: number;
  marketTotal?: number | null;
  sources?: SourceStatus[];
  partial?: boolean;
  from_cache?: boolean;
};

/**
 * Додає унікальні картки в кінець пулу (порядок API / попереднього сортування).
 * Повний re-sort робимо лише при першому показі та при явній зміні сортування.
 */
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

/** Збільшити display: залишити вже показані картки, дописати невідомі з fullPool. */
function growDisplayStable(shown: Listing[], full: Listing[], targetCount: number): Listing[] {
  if (targetCount <= shown.length) return shown.slice(0, Math.max(0, targetCount));
  const ids = new Set(shown.map(item => item.id));
  const next = [...shown];
  for (const item of full) {
    if (next.length >= targetCount) break;
    if (ids.has(item.id)) continue;
    next.push(item);
    ids.add(item.id);
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
  const [poolSize, setPoolSize] = useState(0);
  const [loadedApiPage, setLoadedApiPage] = useState(0);
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
  /**
   * Остання завантажена сторінка API.
   * Використовуємо для nextPage замість розрахунку по розміру пулу,
   * бо деякі AUTO.RIA стаби можуть не гідруватись → пул менший за очікуваний.
   */
  const lastApiPageRef = useRef(0);
  const lastSyncedPreferredCurrency = useRef<string | null>(null);
  // AbortController для поточного active-пошуку. При новому запиті старий скасовується,
  // щоб звільнити з'єднання і backend-слоти (не чекати відповідь, яка вже не потрібна).
  const searchAbortRef = useRef<AbortController | null>(null);

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
      signal?: AbortSignal,
    ): Promise<PageResult> => {
      const data = await listingSearch.search(
        buildRequestFilters(nextFilters, nextFreshness),
        apiPage,
        SEARCH_FIRST_BATCH,
        apiSort,
        "preview",
        signal,
      );
      return {
        items: data.items,
        total: data.total,
        pages: data.pages || Math.max(1, Math.ceil((data.total || 0) / SEARCH_FIRST_BATCH)),
        marketTotal: data.market_total,
        sources: data.sources,
        partial: data.partial,
        from_cache: data.from_cache,
      };
    },
    [buildRequestFilters],
  );

  /**
   * Показати count карток.
   * При збільшенні — не чіпаємо вже показані, лише дописуємо нові з кінця пулу.
   * При зменшенні / першому показі — беремо зріз з початку fullPool.
   */
  const applyDisplaySlice = useCallback((count: number) => {
    const full = fullPoolRef.current;
    const clamped = Math.min(Math.max(count, 0), full.length);
    const shown = displayPoolRef.current;
    if (clamped > shown.length && shown.length > 0) {
      displayPoolRef.current = growDisplayStable(shown, full, clamped);
    } else {
      displayPoolRef.current = full.slice(0, clamped);
    }
    displayCountRef.current = displayPoolRef.current.length;
    setResults([...displayPoolRef.current]);
    setPage(Math.max(1, Math.ceil(displayCountRef.current / SEARCH_PAGE_SIZE)));
  }, []);

  /**
   * Для зміни сортування: пересортовуємо весь fullPool і замінюємо displayPool.
   * Викликається лише при явній зміні sort-опції користувачем.
   */
  const applySortedView = useCallback((sortKey: SortOption, count: number) => {
    const sorted = sortListingItems(fullPoolRef.current, sortKey);
    fullPoolRef.current = sorted;
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
    setPages(Math.max(data.pages || 0, Math.ceil(data.total / SEARCH_PAGE_SIZE) || 0));
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
        let apiPage = lastApiPageRef.current + 1;
        const maxApiPage = Math.max(1, Math.ceil(targetTotal / SEARCH_FIRST_BATCH));
        let emptyPages = 0;

        while (
          gen === searchGen.current &&
          fullPoolRef.current.length < targetTotal &&
          apiPage <= maxApiPage &&
          emptyPages < 2
        ) {
          const prevLen = fullPoolRef.current.length;
          const data = await searchSlice(nextFilters, apiSort, nextFreshness, apiPage);
          if (gen !== searchGen.current) return;
          fullPoolRef.current = appendUniqueToPool(fullPoolRef.current, data.items);
          lastApiPageRef.current = Math.max(lastApiPageRef.current, apiPage);
          setPoolSize(fullPoolRef.current.length);
          setLoadedApiPage(lastApiPageRef.current);
          apiPage += 1;
          // Зупиняємось тільки якщо API дійсно не повернув нічого (не плутаємо з дедупом)
          if (data.items.length === 0) {
            emptyPages += 1;
          } else {
            emptyPages = 0;
          }
          if (fullPoolRef.current.length === prevLen && data.items.length < SEARCH_FIRST_BATCH) {
            // Дедуп + мало items: не прогрес, але продовжимо ще 1 сторінку
            if (data.items.length === 0) break;
          }
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
      options?: RunSearchOptions,
    ) => {
      const background = Boolean(options?.background);
      // Скасовуємо попередній пошук, щоб звільнити backend-слоти і з'єднання.
      searchAbortRef.current?.abort();
      const controller = new AbortController();
      searchAbortRef.current = controller;
      const signal = controller.signal;

      const gen = ++searchGen.current;
      setSearching(true);
      setError(null);
      setErrorRetryAfter(null);
      if (!background) {
        fullPoolRef.current = [];
        displayPoolRef.current = [];
        displayCountRef.current = 0;
        lastApiPageRef.current = 0;
        setPoolSize(0);
        setLoadedApiPage(0);
        scrollToProgress();
      }
      poolApiSortRef.current = nextSort;

      try {
        void fx.rates();
        const first = await searchSlice(nextFilters, nextSort, nextFreshness, 1, signal);
        if (gen !== searchGen.current) return;
        lastApiPageRef.current = 1;

        // Бекенд повертає результати у відсортованому порядку (newest → oldest).
        // Клієнтське сортування — додаткова страховка (пул міг бути з іншим sort_by).
        const firstItems = sortListingItems(first.items, nextSort);
        fullPoolRef.current = [...firstItems];
        // Показуємо одразу до SEARCH_PAGE_SIZE; решту — через «Показати ще».
        const initialDisplay = firstItems.slice(0, SEARCH_PAGE_SIZE);
        displayPoolRef.current = [...initialDisplay];
        displayCountRef.current = initialDisplay.length;

        startTransition(() => {
          setResults([...initialDisplay]);
          setPage(Math.max(1, Math.ceil(initialDisplay.length / SEARCH_PAGE_SIZE)));
          setPoolSize(fullPoolRef.current.length);
          setLoadedApiPage(1);
          syncMeta(first, nextFilters, nextSort, nextFreshness);
          setSearching(false);
        });

        if (first.pages > 1) {
          const second = await searchSlice(nextFilters, nextSort, nextFreshness, 2, signal);
          if (gen !== searchGen.current) return;
          lastApiPageRef.current = 2;
          // Дописуємо стор. 2 у пул — без розширення display (лише preload).
          fullPoolRef.current = appendUniqueToPool(fullPoolRef.current, second.items);
          startTransition(() => {
            setPoolSize(fullPoolRef.current.length);
            setLoadedApiPage(2);
            syncMeta(second, nextFilters, nextSort, nextFreshness);
          });
        }

        void hydrateFullPool(gen, nextFilters, nextFreshness, first.total);
      } catch (err) {
        // AbortError — новий пошук вже запущений; мовчки ігноруємо.
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (gen !== searchGen.current) return;
        if (!background) {
          fullPoolRef.current = [];
          displayPoolRef.current = [];
          displayCountRef.current = 0;
          setResults([]);
          setTotal(0);
          setPage(1);
          setPages(0);
          setPoolSize(0);
          setLoadedApiPage(0);
          setSourceStatuses([]);
          setPartial(false);
          setFromCache(false);
          setRunning(false);
        }
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
      // Починаємо з наступної після останньої завантаженої сторінки,
      // а не розраховуємо по розміру пулу — пул може бути меншим через провал гідрації.
      let apiPage = lastApiPageRef.current + 1;
      let lastMeta: PageResult | null = null;
      let emptyPages = 0;

      for (let attempt = 0; attempt < 6; attempt += 1) {
        if (fullPoolRef.current.length >= targetDisplay) break;
        if (emptyPages >= 2) break;
        const data = await searchSlice(nextFilters, apiSort, nextFreshness, apiPage);
        if (gen !== searchGen.current) return;
        lastMeta = data;
        fullPoolRef.current = appendUniqueToPool(fullPoolRef.current, data.items);
        lastApiPageRef.current = Math.max(lastApiPageRef.current, apiPage);
        setPoolSize(fullPoolRef.current.length);
        setLoadedApiPage(lastApiPageRef.current);
        apiPage += 1;
        if (data.items.length === 0) {
          emptyPages += 1;
        } else {
          emptyPages = 0;
        }
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
          setPages(Math.max(lastMeta.pages || 0, Math.ceil(t / SEARCH_PAGE_SIZE) || 0));
        }
      });
    },
    [applyDisplaySlice, searchSlice],
  );

  const loadMore = useCallback(() => {
    if (!running || loadingMore || searching) return;
    const poolLen = fullPoolRef.current.length;
    const canShowMoreFromPool = poolLen > displayCountRef.current;
    const canFetchMorePages = lastApiPageRef.current < pages;
    if (!canShowMoreFromPool && !canFetchMorePages) return;

    const gen = searchGen.current;
    const targetDisplay = displayCountRef.current + SEARCH_PAGE_SIZE;

    // Вже є в fullPool — просто додаємо в кінець display
    if (fullPoolRef.current.length >= targetDisplay) {
      applyDisplaySlice(targetDisplay);
      return;
    }

    if (!canFetchMorePages || fullPoolRef.current.length >= total) {
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
    pages,
    total,
  ]);

  const runSearch = useCallback(
    async (
      nextFilters: SearchFilterState,
      nextFreshness: SearchFreshness = freshness,
      nextSort: SortOption = sort,
      options?: RunSearchOptions,
    ) => {
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
      setSort(nextSort);
      setFreshness(nextFreshness);
      await fetchInitial(sanitized, nextSort, nextFreshness, options);
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
    setPoolSize(0);
    setLoadedApiPage(0);
    setSourceStatuses([]);
    setPartial(false);
    setFromCache(false);
    setSort("newest");
    setFreshness("new");
    setRunning(false);
    setError(null);
    setErrorRetryAfter(null);
    clearSearchSession();
  }, [user?.preferred_currency]);

  const createSnapshot = useCallback((): SearchSessionSnapshot => {
    return {
      filters,
      freshness,
      sort,
      running,
      results: displayPoolRef.current.length > 0 ? [...displayPoolRef.current] : [...results],
      total,
      marketTotal,
      page,
      pages,
      poolSize: fullPoolRef.current.length,
      loadedApiPage: lastApiPageRef.current,
      sourceStatuses,
      partial,
      fromCache,
      savedAt: Date.now(),
    };
  }, [
    filters,
    freshness,
    sort,
    running,
    results,
    total,
    marketTotal,
    page,
    pages,
    sourceStatuses,
    partial,
    fromCache,
  ]);

  const restoreSnapshot = useCallback((snapshot: SearchSessionSnapshot) => {
    searchGen.current += 1;
    searchAbortRef.current?.abort();

    const items = [...snapshot.results];
    fullPoolRef.current = items;
    displayPoolRef.current = items;
    displayCountRef.current = items.length;
    lastApiPageRef.current = snapshot.loadedApiPage;
    poolApiSortRef.current = snapshot.sort;

    setFilters({ ...snapshot.filters });
    setFreshness(snapshot.freshness);
    setSort(snapshot.sort);
    setResults(items);
    setTotal(snapshot.total);
    setMarketTotal(snapshot.marketTotal);
    setPage(snapshot.page);
    setPages(snapshot.pages);
    setPoolSize(snapshot.poolSize);
    setLoadedApiPage(snapshot.loadedApiPage);
    setSourceStatuses(snapshot.sourceStatuses);
    setPartial(snapshot.partial);
    setFromCache(snapshot.fromCache);
    setRunning(snapshot.running);
    setSearching(false);
    setLoadingMore(false);
    setError(null);
    setErrorRetryAfter(null);
  }, []);

  const restoreFromRecentCache = useCallback(
    (
      nextFilters: SearchFilterState,
      nextFreshness: SearchFreshness,
      cache: RecentSearchResultCache,
      nextSort: SortOption = cache.sort,
    ) => {
      searchGen.current += 1;
      searchAbortRef.current?.abort();

      const items = [...cache.results];
      fullPoolRef.current = items;
      displayPoolRef.current = items;
      displayCountRef.current = items.length;
      lastApiPageRef.current = Math.min(2, Math.max(1, cache.pages));
      poolApiSortRef.current = nextSort;

      setFilters({ ...nextFilters });
      setFreshness(nextFreshness);
      setSort(nextSort);
      setResults(items);
      setTotal(cache.total);
      setMarketTotal(cache.marketTotal);
      setPage(Math.max(1, Math.ceil(items.length / SEARCH_PAGE_SIZE)));
      setPages(cache.pages);
      setPoolSize(items.length);
      setLoadedApiPage(lastApiPageRef.current);
      setSourceStatuses([]);
      setPartial(false);
      setFromCache(true);
      setRunning(true);
      setSearching(false);
      setLoadingMore(false);
      setError(null);
      setErrorRetryAfter(null);
    },
    [],
  );

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
    hasMore:
      running &&
      (results.length < poolSize || (loadedApiPage < pages && pages > 1)),
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
    createSnapshot,
    restoreSnapshot,
    restoreFromRecentCache,
    clearError: () => {
      setError(null);
      setErrorRetryAfter(null);
    },
  };
}
