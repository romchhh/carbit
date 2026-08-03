"use client";

import { useCallback, useEffect, useRef, type RefObject } from "react";
import type { SearchFilterState } from "@/lib/search-catalog";
import {
  saveRecentSearch,
  type RecentSearchEntry,
} from "@/lib/recent-searches";
import type { SearchFreshness } from "@/lib/search-preview";
import type { Listing } from "@/types/api";

type Options = {
  filters: SearchFilterState;
  freshness: SearchFreshness;
  searching: boolean;
  results: Listing[];
  setFilters: (filters: SearchFilterState) => void;
  changeFreshness: (freshness: SearchFreshness) => void;
  scrollTargetRef: RefObject<HTMLElement | null>;
  onBeforeSelect?: () => void;
};

export function useRecentSearches({
  filters,
  freshness,
  searching,
  results,
  setFilters,
  changeFreshness,
  scrollTargetRef,
  onBeforeSelect,
}: Options) {
  const pendingRecentPreviewRef = useRef<{
    filters: SearchFilterState;
    freshness: SearchFreshness;
  } | null>(null);
  const wasSearchingRef = useRef(false);

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
    const previewImage = results[0]?.images?.[0] ?? null;
    if (!previewImage) return;
    saveRecentSearch(pending.filters, pending.freshness, { previewImage });
  }, [searching, results]);

  const handleRecentSelect = useCallback(
    (entry: RecentSearchEntry) => {
      onBeforeSelect?.();
      setFilters({ ...entry.filters });
      changeFreshness(entry.freshness);
      window.requestAnimationFrame(() => {
        scrollTargetRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
          inline: "nearest",
        });
      });
    },
    [changeFreshness, onBeforeSelect, scrollTargetRef, setFilters],
  );

  return { trackSearchStart, handleRecentSelect };
}
