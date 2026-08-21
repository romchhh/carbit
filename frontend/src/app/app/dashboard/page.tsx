"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { IconArrowRight } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import { RecentListingsSection } from "@/components/listings/RecentListingsSection";
import { FavoriteListingsSection } from "@/components/listings/FavoriteListingsSection";
import { FreshListingsCarousel } from "@/components/listings/FreshListingsCarousel";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { MobileSearchFiltersFab } from "@/components/search/MobileSearchFiltersFab";
import { DesktopSearchMonitorFab } from "@/components/search/DesktopSearchMonitorFab";
import { SearchDesktopSplit } from "@/components/search/SearchDesktopSplit";
import { SearchPreviewResults } from "@/components/search/SearchPreviewResults";
import { RecentSearchesSection } from "@/components/search/RecentSearchesSection";
import { TelegramConnectPrompt } from "@/components/search/TelegramConnectPrompt";
import { MonitorSearchCard } from "@/components/search/MonitorSearchCard";
import { UpgradeOffer } from "@/components/billing/UpgradeOffer";
import { SubscriptionPitch } from "@/components/billing/SubscriptionPitch";
import { useAuth } from "@/contexts/AuthProvider";
import { usePreviewSearch } from "@/hooks/usePreviewSearch";
import { useRecentSearches } from "@/hooks/useRecentSearches";
import { useSaveSearch } from "@/hooks/useSaveSearch";
import { searches as searchesApi, users as usersApi } from "@/lib/api";
import { findMatchingSearch } from "@/lib/search-filters-api";
import {
  AppEmpty,
  AppLoading,
  AppPage,
} from "@/components/layout/AppPage";
import { DashboardWelcomeHero } from "@/components/layout/DashboardWelcomeHero";
import { hasSearchDraft } from "@/lib/search-draft";
import type { SearchQuery, DashboardStats } from "@/types/api";

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [searches, setSearches] = useState<SearchQuery[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);
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
  const filtersPanelRef = useRef<HTMLDivElement>(null);
  const [tgPromptOpen, setTgPromptOpen] = useState(false);
  const { saveSearch, saving, saveSuccess, saveError, saveLimitReached, clearSaveMessages } =
    useSaveSearch(created => {
      setSearches(prev => [created, ...prev.filter(s => s.id !== created.id)]);
    });
  const { trackSearchStart, handleRecentSelect } = useRecentSearches({
    filters,
    freshness,
    searching,
    results,
    setFilters,
    changeFreshness,
    scrollTargetRef: filtersPanelRef,
    onBeforeSelect: () => {
      clearSaveMessages();
      clearError();
    },
  });
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const matchingMonitor = useMemo(
    () => findMatchingSearch(searches, filters),
    [searches, filters],
  );

  useEffect(() => {
    if (hasSearchDraft()) {
      router.replace("/app/search");
    }
  }, [router]);

  useEffect(() => {
    searchesApi.list()
      .then(setSearches)
      .catch(() => setSearches([]))
      .finally(() => setLoading(false));
    usersApi.dashboard().then(setStats).catch(() => {});
  }, []);

  if (!user) return null;

  const firstName = user.name.split(" ")[0];
  const activeCount = searches.filter(s => s.is_active).length;
  const limit = user.searches_limit;
  const remaining = Math.max(0, limit - activeCount);
  const totalNew = searches.reduce((sum, s) => sum + s.new_count, 0);

  const setActive = async (search: SearchQuery, active: boolean) => {
    if (search.is_active === active || togglingId) return;
    if (active && remaining <= 0) return;
    setTogglingId(search.id);
    const previous = searches;
    setSearches(list =>
      list.map(item => (item.id === search.id ? { ...item, is_active: active } : item)),
    );
    try {
      const updated = await searchesApi.update(search.id, { is_active: active });
      setSearches(list => list.map(item => (item.id === updated.id ? updated : item)));
    } catch {
      setSearches(previous);
    } finally {
      setTogglingId(null);
    }
  };

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
    if (!user.telegram_connected) {
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
      telegramConnected={user.telegram_connected}
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
    <AppPage wide className="lg:max-w-none">
      <DashboardWelcomeHero firstName={firstName} />

      {(user.plan === "free" || (remaining <= 2 && remaining > 0)) && (
        <SubscriptionPitch
          className="mb-6"
          variant="compact"
          planId={user.plan}
          searchesLimit={limit}
          searchesUsed={activeCount}
          isTrial={Boolean(user.is_trial_active)}
        />
      )}

      <div className="mb-8">
        <h2 className="text-[17px] font-bold text-ink">Новий моніторинг</h2>
        <div className="mt-4">
          <SearchDesktopSplit
            filtersRef={filtersPanelRef}
            filters={filtersPanel}
            results={resultsPanel}
          />
        </div>
      </div>

      <div className="mt-8 flex items-end justify-between gap-3" data-tour="my-searches">
        <div>
          <h2 className="text-[17px] font-bold text-ink">Мої моніторинги</h2>
          <p className="mt-1 text-[13px] text-muted">
            {activeCount} активних · {remaining > 0 ? `ще ${remaining} доступно` : "ліміт використано"}
            {totalNew > 0 ? ` · ${totalNew} нових` : ""}
          </p>
        </div>
        <Link href="/app/monitors" className="shrink-0">
          <Button variant="secondary" size="sm" className="gap-1.5">
            Усі <IconArrowRight size={13} />
          </Button>
        </Link>
      </div>

      {remaining <= 0 && (
        <UpgradeOffer className="mb-5 mt-4" title="Ліміт моніторингів вичерпано" compact />
      )}

      <div className="mt-4">
        {loading ? (
          <AppLoading />
        ) : searches.length === 0 ? (
          <AppEmpty>
            <p className="text-[15px] font-medium text-ink">Поки немає збережених моніторингів</p>
            <p className="mx-auto mt-2 max-w-sm text-[13px] text-muted">
              Налаштуйте фільтри вище і натисніть «Зберегти» — поточні й нові авто з’являться в
              розділі «Мої моніторинги».
            </p>
          </AppEmpty>
        ) : (
          <div className="space-y-3">
            {searches.slice(0, 3).map(s => (
              <MonitorSearchCard
                key={s.id}
                search={s}
                alwaysLink={false}
                toggling={togglingId === s.id}
                onActiveChange={active => void setActive(s, active)}
              />
            ))}
            {searches.length > 3 && (
              <Link
                href="/app/monitors"
                className="block rounded-2xl border border-dashed border-border bg-white px-4 py-3 text-center text-[13px] font-semibold text-emerald-dark hover:border-emerald/40"
              >
                Ще {searches.length - 3} моніторингів →
              </Link>
            )}
          </div>
        )}
      </div>

      <RecentListingsSection className="mb-10" />

      <FavoriteListingsSection className="mb-10" />

      <RecentSearchesSection onSelect={handleRecentSelect} />

      <div className="mt-10">
        <FreshListingsCarousel variant="dashboard" />
      </div>

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
    </AppPage>
  );
}
