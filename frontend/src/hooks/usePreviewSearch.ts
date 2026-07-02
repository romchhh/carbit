"use client";

import { useCallback, useRef, useState } from "react";
import { autoRia, getApiErrorMessage } from "@/lib/api";
import { DEFAULT_FILTERS, type SearchFilterState } from "@/lib/search-catalog";
import { PREVIEW_RESULTS_LIMIT } from "@/lib/search-preview";
import { toBackendSearchFilters } from "@/lib/search-filters-api";
import type { Listing } from "@/types/api";

export function usePreviewSearch(initialFilters: SearchFilterState = { ...DEFAULT_FILTERS }) {
  const resultsRef = useRef<HTMLDivElement>(null);
  const [filters, setFilters] = useState<SearchFilterState>(initialFilters);
  const [results, setResults] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [running, setRunning] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(async (nextFilters: SearchFilterState) => {
    setSearching(true);
    setError(null);

    requestAnimationFrame(() => {
      resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    try {
      const data = await autoRia.search(
        toBackendSearchFilters(nextFilters),
        1,
        PREVIEW_RESULTS_LIMIT,
        "price_asc",
        "preview",
      );
      setResults(data.items.slice(0, PREVIEW_RESULTS_LIMIT));
      setTotal(data.total);
      setFilters({ ...nextFilters });
      setRunning(true);
    } catch (err) {
      setResults([]);
      setTotal(0);
      setRunning(false);
      setError(getApiErrorMessage(err, "Не вдалось виконати пошук. Спробуйте ще раз."));
    } finally {
      setSearching(false);
    }
  }, []);

  const reset = useCallback(() => {
    setFilters({ ...DEFAULT_FILTERS });
    setResults([]);
    setTotal(0);
    setRunning(false);
    setError(null);
  }, []);

  return {
    filters,
    setFilters,
    results,
    total,
    running,
    searching,
    error,
    resultsRef,
    runSearch,
    reset,
    clearError: () => setError(null),
  };
}
