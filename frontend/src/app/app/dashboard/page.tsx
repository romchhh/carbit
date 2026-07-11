"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { IconPlus, IconZap, IconArrowRight } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { RecentListingsSection } from "@/components/listings/RecentListingsSection";
import { FavoriteListingsSection } from "@/components/listings/FavoriteListingsSection";
import { FreshListingsCarousel } from "@/components/listings/FreshListingsCarousel";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { SearchPreviewResults } from "@/components/search/SearchPreviewResults";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { usePreviewSearch } from "@/hooks/usePreviewSearch";
import { useSaveSearch } from "@/hooks/useSaveSearch";
import { searches as searchesApi, users as usersApi } from "@/lib/api";
import {
  AppEmpty,
  AppLoading,
  AppPage,
  AppSection,
} from "@/components/layout/AppPage";
import { DashboardWelcomeHero } from "@/components/layout/DashboardWelcomeHero";
import type { SearchQuery, DashboardStats } from "@/types/api";

function formatSearchDesc(filters: Record<string, unknown>): string {
  const parts: string[] = [];
  if (filters.brand) parts.push(String(filters.brand));
  if (filters.model) parts.push(String(filters.model));
  if (filters.year_from || filters.year_to) {
    parts.push(`${filters.year_from ?? "…"}–${filters.year_to ?? "…"}`);
  }
  if (filters.price_from || filters.price_to) {
    const from = filters.price_from ? Number(filters.price_from).toLocaleString("uk-UA") : "…";
    const to = filters.price_to ? Number(filters.price_to).toLocaleString("uk-UA") : "…";
    const currency = filters.currency === "USD" ? "$" : "грн";
    parts.push(`${from}–${to} ${currency}`);
  }
  if (filters.region) parts.push(String(filters.region));
  return parts.length > 0 ? parts.join(" · ") : "Без фільтрів";
}

function CompactStat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-xl border border-border/40 bg-white px-3 py-3 sm:px-4 sm:py-3.5">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 text-[20px] font-bold leading-none text-ink sm:text-[22px]">{value}</div>
      {sub && (
        <div className={cn("mt-1 text-[11px]", accent ? "font-medium text-emerald-dark" : "text-muted")}>
          {sub}
        </div>
      )}
    </div>
  );
}

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

  const statsCards = stats
    ? [
        { label: "Активних", value: stats.active_searches, sub: `з ${stats.searches_limit}` },
        { label: "Нових сьогодні", value: stats.new_listings_today, sub: `${stats.new_listings_yesterday} вчора`, accent: stats.new_listings_today > 0 },
        { label: "В обраному", value: stats.favorites_count, sub: "авто" },
        { label: "Сповіщень", value: stats.unread_notifications, sub: "непрочитаних", accent: stats.unread_notifications > 0 },
      ]
    : [
        { label: "Активних", value: activeCount, sub: `з ${limit}` },
        { label: "Нових", value: totalNew, sub: "за добу", accent: totalNew > 0 },
        { label: "Запитів", value: searches.length, sub: "всього" },
        { label: "Джерел", value: "3", sub: "AUTO.RIA · OLX · TG" },
      ];

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
    void saveSearch(filters);
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
          onSortChange={changeSort}
          onFreshnessChange={changeFreshness}
          onLoadMore={loadMore}
          onSave={handleSave}
          saving={saving}
          telegramConnected={user.telegram_connected}
        />
      </div>

      <div className="mt-8 flex items-end justify-between gap-3" data-tour="my-searches">
        <div>
          <h2 className="text-[17px] font-bold text-ink">Мої запити</h2>
          <p className="mt-1 text-[13px] text-muted">
            {activeCount} активних · {remaining > 0 ? `ще ${remaining} доступно` : "ліміт використано"}
          </p>
        </div>
        <Link href="/app/search" className="shrink-0">
          <Button variant="secondary" size="sm" className="gap-1.5">
            <IconPlus size={13} /> Додати
          </Button>
        </Link>
      </div>

      <div className="mt-4">
        {loading ? (
          <AppLoading />
        ) : searches.length === 0 ? (
          <AppEmpty>
            <p className="text-[15px] font-medium text-ink">Поки немає збережених запитів</p>
            <p className="mx-auto mt-2 max-w-sm text-[13px] text-muted">
              Налаштуйте фільтри вище і натисніть «Зберегти пошук» — нові авто приходитимуть у Telegram.
            </p>
          </AppEmpty>
        ) : (
          <div className="space-y-3">
            {searches.map(s => (
              <AppSection
                key={s.id}
                className={cn("!bg-white p-4 sm:p-5", !s.is_active && "opacity-60")}
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                  <div className="flex min-w-0 flex-1 items-start gap-3">
                    <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", s.is_active ? "bg-emerald" : "bg-border")} />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="truncate text-[15px] font-semibold text-ink">{s.name}</span>
                        {s.new_count > 0 && (
                          <Badge variant="ink" className="gap-1">
                            <IconZap size={9} /> {s.new_count}
                          </Badge>
                        )}
                      </div>
                      <p className="mt-1 truncate text-[12px] text-muted">{formatSearchDesc(s.filters)}</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-4 sm:justify-end">
                    <div className="text-left sm:text-right">
                      <div className={cn("text-[20px] font-black leading-none", s.is_active ? "text-emerald-dark" : "text-muted")}>
                        {s.is_active ? s.total_count : "—"}
                      </div>
                      <div className="mt-1 text-[10px] uppercase tracking-wide text-muted">знайдено</div>
                    </div>
                    {s.is_active && (
                      <Link
                        href={`/app/results?search=${s.id}`}
                        className="inline-flex items-center gap-1 rounded-full bg-emerald/10 px-3 py-2 text-[12px] font-semibold text-emerald-dark transition-colors hover:bg-emerald/15"
                      >
                        Результати <IconArrowRight size={11} />
                      </Link>
                    )}
                  </div>
                </div>
              </AppSection>
            ))}
          </div>
        )}
      </div>

      <RecentListingsSection className="mb-10" />

      <FavoriteListingsSection className="mb-10" />

      <div className="mt-10">
        <FreshListingsCarousel variant="dashboard" />
      </div>

      <AppSection className="!bg-surface/50 mt-10">
        <h3 className="text-[11px] font-bold uppercase tracking-wide text-muted mb-3">Огляд</h3>
        <div className="grid grid-cols-2 gap-2.5 sm:gap-3 lg:grid-cols-4">
          {statsCards.map(card => (
            <CompactStat key={card.label} {...card} />
          ))}
        </div>
      </AppSection>
    </AppPage>
  );
}
