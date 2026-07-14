"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { IconArrowRight } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import { RecentListingsSection } from "@/components/listings/RecentListingsSection";
import { FavoriteListingsSection } from "@/components/listings/FavoriteListingsSection";
import { FreshListingsCarousel } from "@/components/listings/FreshListingsCarousel";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { SearchPreviewResults } from "@/components/search/SearchPreviewResults";
import { MonitorSearchCard } from "@/components/search/MonitorSearchCard";
import { useAuth } from "@/contexts/AuthProvider";
import { usePreviewSearch } from "@/hooks/usePreviewSearch";
import { useSaveSearch } from "@/hooks/useSaveSearch";
import { searches as searchesApi, users as usersApi } from "@/lib/api";
import {
  AppEmpty,
  AppLoading,
  AppPage,
} from "@/components/layout/AppPage";
import { DashboardWelcomeHero } from "@/components/layout/DashboardWelcomeHero";
import type { SearchQuery, DashboardStats } from "@/types/api";

export default function DashboardPage() {
  const { user } = useAuth();
  const [searches, setSearches] = useState<SearchQuery[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const {
    filters,
    setFilters,
    results,
    total,
    sort,
    freshness,
    running,
    searching,
    loadingMore,
    hasMore,
    error,
    sourceStatuses,
    partial,
    fromCache,
    displayCurrency,
    resultsRef,
    runSearch,
    changeSort,
    changeFreshness,
    loadMore,
    reset,
    clearError,
  } = usePreviewSearch();
  const { saveSearch, saving, saveSuccess, saveError, saveLimitReached, clearSaveMessages } = useSaveSearch(created => {
    setSearches(prev => [created, ...prev]);
  });

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

  const handleSearch = () => {
    clearSaveMessages();
    clearError();
    void runSearch(filters);
  };

  const handleReset = () => {
    clearSaveMessages();
    reset();
  };

  const handleSave = () => {
    void saveSearch(filters, results);
  };

  return (
    <AppPage wide>
      <DashboardWelcomeHero
        firstName={firstName}
        activeSearches={activeCount}
        searchesLimit={limit}
        telegramConnected={user.telegram_connected}
        unreadNotifications={stats?.unread_notifications ?? 0}
      />

      <div className="mb-8">
        <h2 className="text-[17px] font-bold text-ink">Новий моніторинг</h2>
        <p className="mt-1 text-[13px] text-muted">
          Пошук усіх авто за фільтрами. Збережіть запит — далі нові пропозиції приходитимуть автоматично.
        </p>
        <div className="mt-4">
          <SearchFiltersPanel
            wide
            filters={filters}
            onChange={setFilters}
            onReset={handleReset}
            onSearch={handleSearch}
            onSave={handleSave}
            searching={searching}
            searchError={error}
            saving={saving}
            saveSuccess={saveSuccess}
            saveError={saveError}
            saveLimitReached={saveLimitReached}
            telegramConnected={user.telegram_connected}
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
          results={results}
          sort={sort}
          freshness={freshness}
          error={error}
          sourceStatuses={sourceStatuses}
          partial={partial}
          fromCache={fromCache}
          displayCurrency={displayCurrency}
          onSortChange={changeSort}
          onFreshnessChange={changeFreshness}
          onLoadMore={loadMore}
        />
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
              <MonitorSearchCard key={s.id} search={s} alwaysLink={false} />
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

      <div className="mt-10">
        <FreshListingsCarousel variant="dashboard" />
      </div>
    </AppPage>
  );
}
