"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import { usePreviewSearch } from "@/hooks/usePreviewSearch";
import { loadSearchSession, saveSearchSession } from "@/lib/search-session";

type SearchSessionValue = ReturnType<typeof usePreviewSearch>;

const SearchSessionContext = createContext<SearchSessionValue | null>(null);

export function SearchSessionProvider({ children }: { children: ReactNode }) {
  const search = usePreviewSearch();
  const restoredRef = useRef(false);
  const {
    running,
    filters,
    freshness,
    sort,
    results,
    total,
    marketTotal,
    page,
    pages,
    sourceStatuses,
    partial,
    fromCache,
    createSnapshot,
    restoreSnapshot,
  } = search;

  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    const snapshot = loadSearchSession();
    if (snapshot?.running) {
      restoreSnapshot(snapshot);
    }
  }, [restoreSnapshot]);

  useEffect(() => {
    if (!running) return;
    const timer = window.setTimeout(() => {
      saveSearchSession(createSnapshot());
    }, 350);
    return () => window.clearTimeout(timer);
  }, [
    running,
    filters,
    freshness,
    sort,
    results,
    total,
    marketTotal,
    page,
    pages,
    sourceStatuses,
    partial,
    fromCache,
    createSnapshot,
  ]);

  return (
    <SearchSessionContext.Provider value={search}>{children}</SearchSessionContext.Provider>
  );
}

export function useSearchSession(): SearchSessionValue {
  const ctx = useContext(SearchSessionContext);
  if (!ctx) {
    throw new Error("useSearchSession must be used within SearchSessionProvider");
  }
  return ctx;
}
