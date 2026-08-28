"use client";

import { useCallback, type RefObject } from "react";
import type { SearchFilterState, SortOption } from "@/lib/search-catalog";
import { saveRecentSearch, type RecentSearchEntry } from "@/lib/recent-searches";
import {
  isRecentCacheFresh,
  shouldRefreshRecentCache,
} from "@/lib/recent-search-cache";
import type { SearchFreshness } from "@/lib/search-preview";
import type { RecentSearchResultCache } from "@/lib/recent-search-cache";

type Options = {
  freshness: SearchFreshness;
  sort: SortOption;
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
  freshness,
  sort,
  setFilters,
  changeFreshness,
  runSearch,
  restoreFromRecentCache,
  scrollTargetRef,
  onBeforeSelect,
}: Options) {
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
    (nextFilters: SearchFilterState, nextFreshness?: SearchFreshness) => {
      saveRecentSearch(nextFilters, nextFreshness ?? freshness);
    },
    [freshness],
  );

  const handleRecentSelect = useCallback(
    (entry: RecentSearchEntry) => {
      onBeforeSelect?.();
      const cache = entry.cache;

      if (cache && isRecentCacheFresh(cache)) {
        saveRecentSearch(entry.filters, entry.freshness, {
          previewImage: entry.previewImage,
        });
        restoreFromRecentCache(entry.filters, entry.freshness, cache, cache.sort);
        scrollToSearch();
        if (shouldRefreshRecentCache(cache)) {
          void runSearch(entry.filters, entry.freshness, cache.sort, { background: true });
        }
        return;
      }

      setFilters({ ...entry.filters });
      changeFreshness(entry.freshness);
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
    ],
  );

  return { trackSearchStart, handleRecentSelect };
}
