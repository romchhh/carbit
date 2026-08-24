"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { MobileSearchFiltersFab } from "@/components/search/MobileSearchFiltersFab";
import { DesktopSearchMonitorFab } from "@/components/search/DesktopSearchMonitorFab";
import { SearchDesktopSplit } from "@/components/search/SearchDesktopSplit";
import { SearchPreviewResults } from "@/components/search/SearchPreviewResults";
import { RecentSearchesSection } from "@/components/search/RecentSearchesSection";
import { TelegramConnectPrompt } from "@/components/search/TelegramConnectPrompt";
import { useAuth } from "@/contexts/AuthProvider";
import { useSearchSession } from "@/contexts/SearchSessionProvider";
import { useRecentSearches } from "@/hooks/useRecentSearches";
import { useSaveSearch } from "@/hooks/useSaveSearch";
import { RecentListingsSection } from "@/components/listings/RecentListingsSection";
import { searches as searchesApi } from "@/lib/api";
import { findMatchingSearch } from "@/lib/search-filters-api";
import {
  beginSearchDraftAutoRun,
  clearSearchDraft,
  peekSearchDraft,
} from "@/lib/search-draft";
import type { SearchQuery } from "@/types/api";

export default function SearchPage() {
  const router = useRouter();
  const { user, loading: authLoading, initialized } = useAuth();
  const [searches, setSearches] = useState<SearchQuery[]>([]);
  const [tgPromptOpen, setTgPromptOpen] = useState(false);
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
    page,
    pages,
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
    restoreFromRecentCache,
  } = useSearchSession();

  const filtersPanelRef = useRef<HTMLDivElement>(null);
  const { trackSearchStart, handleRecentSelect } = useRecentSearches({
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
    scrollTargetRef: filtersPanelRef,
    onBeforeSelect: () => {
      clearSaveMessages();
      clearError();
    },
  });

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
    trackSearchStart(draft.filters, draft.freshness);
    void runSearch(draft.filters, draft.freshness);
  }, [initialized, authLoading, user, runSearch, changeFreshness, trackSearchStart]);

  const handleSearch = (
    overrideFilters?: typeof filters,
    overrideSort?: Parameters<typeof runSearch>[2],
  ) => {
    clearSaveMessages();
    clearError();
    trackSearchStart(overrideFilters);
    void runSearch(overrideFilters ?? filters, freshness, overrideSort);
  };

  const handleReset = () => {
    clearSaveMessages();
    reset();
  };

  const handleSave = () => {
    void saveSearch(filters, results);
  };

  const handleMonitorClick = () => {
    if (saving || saveLimitReached) return;
    if (matchingMonitor) {
      router.push(`/app/monitors/${matchingMonitor.id}`);
      return;
    }
    if (!user?.telegram_connected) {
      setTgPromptOpen(true);
      return;
    }
    handleSave();
  };

  const filtersPanel = (
    <SearchFiltersPanel
      wide
      variant="sidebar"
      hideDesktopSave
      filters={filters}
      onChange={setFilters}
      onReset={handleReset}
      onSearch={handleSearch}
      onSortChange={changeSort}
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
  );

  const resultsPanel = (
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
  );

  return (
    <div className="lg:max-w-none">
      <RecentListingsSection className="mb-8 lg:hidden" />

      <div className="mb-5 flex flex-col gap-2 sm:mb-7 sm:flex-row sm:items-start sm:justify-between sm:gap-3 lg:mb-6">
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

      <SearchDesktopSplit
        filtersRef={filtersPanelRef}
        filters={filtersPanel}
        results={resultsPanel}
        footer={<RecentSearchesSection onSelect={handleRecentSelect} />}
      />

      <MobileSearchFiltersFab
        targetRef={filtersPanelRef}
        monitor={{
          visible: running,
          connected: Boolean(matchingMonitor),
          connectedMonitorId: matchingMonitor?.id ?? null,
          saving,
          limitReached: saveLimitReached,
          onSave: handleMonitorClick,
        }}
      />

      <DesktopSearchMonitorFab
        visible={running}
        connected={Boolean(matchingMonitor)}
        connectedMonitorId={matchingMonitor?.id ?? null}
        saving={saving}
        limitReached={saveLimitReached}
        onSave={handleMonitorClick}
      />

      <TelegramConnectPrompt
        open={tgPromptOpen}
        onClose={() => setTgPromptOpen(false)}
        onContinueWithoutTelegram={handleSave}
        onConnected={handleSave}
      />
    </div>
  );
}
