"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { SearchPreviewResults } from "@/components/search/SearchPreviewResults";
import { RecentSearchesSection } from "@/components/search/RecentSearchesSection";
import { useAuth } from "@/contexts/AuthProvider";
import { usePreviewSearch } from "@/hooks/usePreviewSearch";
import { useSaveSearch } from "@/hooks/useSaveSearch";
import { RecentListingsSection } from "@/components/listings/RecentListingsSection";
import { searches as searchesApi } from "@/lib/api";
import { findMatchingSearch } from "@/lib/search-filters-api";
import {
  beginSearchDraftAutoRun,
  clearSearchDraft,
  peekSearchDraft,
} from "@/lib/search-draft";
import {
  saveRecentSearch,
  type RecentSearchEntry,
} from "@/lib/recent-searches";
import type { SearchQuery } from "@/types/api";

export default function SearchPage() {
  const { user, loading: authLoading, initialized } = useAuth();
  const [searches, setSearches] = useState<SearchQuery[]>([]);
  const { saveSearch, saving, saveSuccess, saveError, saveLimitReached, clearSaveMessages } =
    useSaveSearch(created => {
      setSearches(prev => [created, ...prev.filter(s => s.id !== created.id)]);
    });
  const {
    filters,
    setFilters,
    results,
    total,
    marketTotal,
    sort,
    freshness,
    running,
    searching,
    loadingMore,
    hasMore,
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
    clearError,
  } = usePreviewSearch();

  useEffect(() => {
    if (!initialized || authLoading || !user) return;
    searchesApi
      .list()
      .then(setSearches)
      .catch(() => setSearches([]));
  }, [initialized, authLoading, user]);

  const matchingMonitor = useMemo(
    () => findMatchingSearch(searches, filters),
    [searches, filters],
  );

  useEffect(() => {
    if (!initialized || authLoading || !user) return;
    const draft = peekSearchDraft();
    if (!draft || !beginSearchDraftAutoRun()) return;

    changeFreshness(draft.freshness);
    clearSearchDraft();
    saveRecentSearch(draft.filters, draft.freshness);
    void runSearch(draft.filters, draft.freshness);
  }, [initialized, authLoading, user, runSearch, changeFreshness]);

  const handleSearch = () => {
    clearSaveMessages();
    clearError();
    saveRecentSearch(filters, freshness);
    void runSearch(filters);
  };

  const handleRecentSelect = useCallback(
    (entry: RecentSearchEntry) => {
      clearSaveMessages();
      clearError();
      setFilters({ ...entry.filters });
      changeFreshness(entry.freshness);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [changeFreshness, clearError, clearSaveMessages, setFilters],
  );

  const handleReset = () => {
    clearSaveMessages();
    reset();
  };

  const handleSave = () => {
    void saveSearch(filters, results);
  };

  return (
    <div className="max-w-[1100px]">
      <RecentListingsSection className="mb-8" />
      <div className="mb-5 flex flex-col gap-2 sm:mb-7 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
        <div>
          <h1 className="text-[22px] font-black tracking-[-0.02em] text-ink sm:text-[26px]">
            Пошук авто
          </h1>
          <p className="mt-1 max-w-[560px] text-[12px] leading-relaxed text-muted sm:text-[13px]">
            AUTO.RIA, OLX і Telegram в одному пошуку — усі авто або лише свіжі за тиждень.
          </p>
        </div>
        <span className="flex w-fit flex-col items-end gap-1 sm:items-end">
          <span className="rounded-lg border border-border bg-surface px-3 py-1.5 text-[11px] text-muted sm:bg-white sm:text-[12px]">
            До <strong className="text-ink">{user?.searches_limit ?? "—"}</strong> збережених
            моніторингів
          </span>
          {user && (
            <Link
              href="/app/billing"
              className="text-[11px] font-semibold text-emerald-dark hover:underline"
            >
              {user.plan === "free" ? "Оформити підписку →" : "Змінити тариф →"}
            </Link>
          )}
        </span>
      </div>

      <div className="mb-5 sm:mb-6">
        <SearchFiltersPanel
          wide
          filters={filters}
          onChange={setFilters}
          onReset={handleReset}
          onSearch={handleSearch}
          onSave={handleSave}
          searching={searching}
          searchError={error}
          searchErrorRetryAfter={errorRetryAfter}
          saving={saving}
          saveSuccess={saveSuccess}
          saveError={saveError}
          saveLimitReached={saveLimitReached}
          telegramConnected={user?.telegram_connected}
          monitorConnected={Boolean(matchingMonitor)}
          connectedMonitorId={matchingMonitor?.id ?? null}
          freshness={freshness}
          onFreshnessChange={changeFreshness}
        />
      </div>

      <SearchPreviewResults
        resultsRef={resultsRef}
        running={running}
        searching={searching}
        loadingMore={loadingMore}
        hasMore={hasMore}
        total={total}
        marketTotal={marketTotal}
        results={results}
        sort={sort}
        freshness={freshness}
        error={error}
        sourceStatuses={sourceStatuses}
        partial={partial}
        fromCache={fromCache}
        onSortChange={changeSort}
        onFreshnessChange={changeFreshness}
        onLoadMore={loadMore}
      />

      <RecentSearchesSection onSelect={handleRecentSelect} />
    </div>
  );
}
