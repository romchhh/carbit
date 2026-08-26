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
import { useSearchSession } from "@/contexts/SearchSessionProvider";
import { useRecentSearches } from "@/hooks/useRecentSearches";
import { useSaveSearch } from "@/hooks/useSaveSearch";
import { searches as searchesApi, users as usersApi } from "@/lib/api";
import { findMatchingSearch } from "@/lib/search-filters-api";
import { DashboardScrollRow } from "@/components/layout/DashboardScrollRow";
import {
  AppEmpty,
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
  const [tgPromptOpen, setTgPromptOpen] = useState(false);
  const { saveSearch, saving, saveSuccess, saveError, saveLimitReached, clearSaveMessages } =
    useSaveSearch(created => {
      setSearches(prev => [created, ...prev.filter(s => s.id !== created.id)]);
    });
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
  const totalPriceDrops = searches.reduce((sum, s) => sum + (s.price_drop_count || 0), 0);

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

  const renderFiltersPanel = (options?: { inModal?: boolean; onClose?: () => void }) => (
    <SearchFiltersPanel
      wide
      variant="sidebar"
      inModal={options?.inModal}
      filters={filters}
      onChange={setFilters}
      onReset={handleReset}
      onSearch={(overrideFilters, overrideSort) => {
        handleSearch(overrideFilters, overrideSort);
        options?.onClose?.();
      }}
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
      monitorSlot={
        <DesktopSearchMonitorFab
          connected={Boolean(matchingMonitor)}
          connectedMonitorId={matchingMonitor?.id ?? null}
          saving={saving}
          limitReached={saveLimitReached}
          onSave={handleMonitorClick}
        />
      }
    />
  );

  const filtersPanel = renderFiltersPanel();

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
        <SearchDesktopSplit
          filtersRef={filtersPanelRef}
          filters={filtersPanel}
          results={resultsPanel}
        />
      </div>

      <RecentSearchesSection className="mb-8" onSelect={handleRecentSelect} />

      <div className="mb-8 space-y-5">
        <DashboardScrollRow
          tourId="my-searches"
          title="Мої моніторинги"
          description={[
            `${activeCount} активних`,
            remaining > 0 ? `ще ${remaining} доступно` : "ліміт використано",
            totalNew > 0 ? `${totalNew} нових` : "",
            totalPriceDrops > 0 ? `${totalPriceDrops} зі зниженням` : "",
          ]
            .filter(Boolean)
            .join(" · ")}
          action={
            <Link href="/app/monitors">
              <Button variant="secondary" size="sm" className="gap-1.5">
                Усі <IconArrowRight size={13} />
              </Button>
            </Link>
          }
          isEmpty={!loading && searches.length === 0}
          empty={
            <AppEmpty className="!py-8">
              <p className="text-[14px] font-medium text-ink">Поки немає збережених моніторингів</p>
              <p className="mx-auto mt-2 max-w-sm text-[12px] text-muted">
                Налаштуйте фільтри вище і натисніть «Зберегти» — поточні й нові авто з&apos;являться тут.
              </p>
            </AppEmpty>
          }
        >
          {loading ? (
            <div className="flex h-[220px] w-full items-center justify-center">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
            </div>
          ) : (
            searches.map(s => (
              <MonitorSearchCard
                key={s.id}
                search={s}
                variant="compact"
                alwaysLink={false}
                toggling={togglingId === s.id}
                onActiveChange={active => void setActive(s, active)}
              />
            ))
          )}
        </DashboardScrollRow>

        {remaining <= 0 && (
          <UpgradeOffer title="Ліміт моніторингів вичерпано" compact />
        )}
      </div>

      <RecentListingsSection className="mb-10" />

      <FavoriteListingsSection className="mb-10" />

      <div className="mt-10">
        <FreshListingsCarousel variant="dashboard" />
      </div>

      <MobileSearchFiltersFab
        targetRef={filtersPanelRef}
        renderFilters={close => renderFiltersPanel({ inModal: true, onClose: close })}
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
