"use client";

import { useCallback, useEffect, useRef, type RefObject } from "react";
import type { SearchFilterState, SortOption } from "@/lib/search-catalog";
import {
  saveRecentSearch,
  updateRecentSearchCache,
  type RecentSearchEntry,
} from "@/lib/recent-searches";
import {
  buildRecentSearchCache,
  isRecentCacheFresh,
  shouldRefreshRecentCache,
} from "@/lib/recent-search-cache";
import type { SearchFreshness } from "@/lib/search-preview";
import type { Listing } from "@/types/api";
import type { RecentSearchResultCache } from "@/lib/recent-search-cache";

type Options = {
  filters: SearchFilterState;
  freshness: SearchFreshness;
  sort: SortOption;
  pages: number;
  total: number;
  marketTotal: number | null;
  searching: boolean;
  results: Listing[];
  setFilters: (filters: SearchFilterState) => void;
  changeFreshness: (freshness: SearchFreshness) => void;
  runSearch: (
    filters: SearchFilterState,
    freshness?: SearchFreshness,
    sort?: SortOption,
    options?: { background?: boolean },
  ) => Promise<void>;
  restoreFromRecentCache: (
    filters: SearchFilterState,
    freshness: SearchFreshness,
    cache: RecentSearchResultCache,
    sort?: SortOption,
  ) => void;
  scrollTargetRef: RefObject<HTMLElement | null>;
  onBeforeSelect?: () => void;
};

export function useRecentSearches({
  filters,
  freshness,
  sort,
  pages,
  total,
  marketTotal,
  searching,
  results,
  setFilters,
  changeFreshness,
  runSearch,
  restoreFromRecentCache,
  scrollTargetRef,
  onBeforeSelect,
}: Options) {
  const pendingRecentPreviewRef = useRef<{
    filters: SearchFilterState;
    freshness: SearchFreshness;
  } | null>(null);
  const wasSearchingRef = useRef(false);

  const scrollToSearch = useCallback(() => {
    window.requestAnimationFrame(() => {
      scrollTargetRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
        inline: "nearest",
      });
    });
  }, [scrollTargetRef]);

  const trackSearchStart = useCallback(
    (nextFilters?: SearchFilterState, nextFreshness?: SearchFreshness) => {
      const f = nextFilters ?? filters;
      const fr = nextFreshness ?? freshness;
      pendingRecentPreviewRef.current = { filters: f, freshness: fr };
      saveRecentSearch(f, fr);
    },
    [filters, freshness],
  );

  useEffect(() => {
    if (searching) {
      wasSearchingRef.current = true;
      return;
    }
    if (!wasSearchingRef.current) return;
    wasSearchingRef.current = false;
    const pending = pendingRecentPreviewRef.current;
    if (!pending) return;
    pendingRecentPreviewRef.current = null;

    const previewImage =
      results.find(item => item.images?.[0])?.images?.[0] ?? null;
    const cache = buildRecentSearchCache(results, total, marketTotal, sort, pages);
    updateRecentSearchCache(pending.filters, pending.freshness, cache, previewImage);
  }, [searching, results, total, marketTotal, sort, pages]);

  const handleRecentSelect = useCallback(
    (entry: RecentSearchEntry) => {
      onBeforeSelect?.();
      const cache = entry.cache;

      if (cache && isRecentCacheFresh(cache)) {
        restoreFromRecentCache(entry.filters, entry.freshness, cache, cache.sort);
        scrollToSearch();
        if (shouldRefreshRecentCache(cache)) {
          trackSearchStart(entry.filters, entry.freshness);
          void runSearch(entry.filters, entry.freshness, cache.sort, { background: true });
        }
        return;
      }

      setFilters({ ...entry.filters });
      changeFreshness(entry.freshness);
      trackSearchStart(entry.filters, entry.freshness);
      scrollToSearch();
      void runSearch(entry.filters, entry.freshness, sort);
    },
    [
      changeFreshness,
      onBeforeSelect,
      restoreFromRecentCache,
      runSearch,
      scrollToSearch,
      setFilters,
      sort,
      trackSearchStart,
    ],
  );

  return { trackSearchStart, handleRecentSelect };
}
