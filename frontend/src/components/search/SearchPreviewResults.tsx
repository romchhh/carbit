"use client";

import { useMemo, useState } from "react";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { SearchPreviewNotice } from "@/components/search/SearchPreviewNotice";
import { SearchResultsSkeleton } from "@/components/search/SearchResultsSkeleton";
import { SearchResultsToolbar } from "@/components/search/SearchResultsToolbar";
import { useListingFavorites } from "@/hooks/useListingFavorite";
import { saveRecentListing } from "@/lib/recent-listings";
import type { SortOption } from "@/lib/search-catalog";
import type { ExportListing } from "@/lib/export-listings";
import { SEARCH_HOURLY_LIMIT, SEARCH_PAGE_SIZE, type SearchFreshness } from "@/lib/search-preview";
import type { Listing } from "@/types/api";
import { cn } from "@/lib/utils";

function sourceLabel(source: string): string {
  if (source === "olx") return "OLX";
  if (source === "auto_ria") return "AUTO.RIA";
  if (source === "telegram") return "Telegram";
  return source.toUpperCase();
}

function toExportItems(items: Listing[]): ExportListing[] {
  return items.map(item => ({
    id: item.id,
    title: item.title,
    year: item.year,
    mileage: item.mileage,
    price: item.price,
    region: item.region,
    src: sourceLabel(item.source),
    fuel: item.fuel,
    trans: item.transmission,
    desc: item.description ?? undefined,
    url: item.url,
  }));
}

type Props = {
  resultsRef: React.RefObject<HTMLDivElement | null>;
  running: boolean;
  searching: boolean;
  loadingMore?: boolean;
  hasMore?: boolean;
  total: number;
  results: Listing[];
  sort: SortOption;
  freshness: SearchFreshness;
  error?: string | null;
  onSortChange: (sort: SortOption) => void;
  onFreshnessChange: (freshness: SearchFreshness) => void;
  onLoadMore?: () => void;
  onSave?: () => void;
  saving?: boolean;
  telegramConnected?: boolean;
};

export function SearchPreviewResults({
  resultsRef,
  running,
  searching,
  loadingMore,
  hasMore,
  total,
  results,
  sort,
  freshness,
  error,
  onSortChange,
  onFreshnessChange,
  onLoadMore,
  onSave,
  saving,
  telegramConnected,
}: Props) {
  const { favoriteIds, loadingIds, error: favoriteError, clearError, toggleFavorite } = useListingFavorites(
    results.map(item => item.id),
  );
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const exportItems = useMemo(() => toExportItems(results), [results]);

  const openListing = (listing: Listing) => {
    saveRecentListing(listing);
    setSelectedListing(listing);
  };

  return (
    <>
      <div ref={resultsRef} className="mt-6 scroll-mt-24 sm:mt-8">
        <div className="mb-3 flex flex-wrap gap-2">
          {(
            [
              { value: "all" as const, label: "Шукати всі" },
              { value: "new" as const, label: "Тільки нові (7 днів)" },
            ] as const
          ).map(option => (
            <button
              key={option.value}
              type="button"
              onClick={() => onFreshnessChange(option.value)}
              className={cn(
                "rounded-full border px-3.5 py-1.5 text-[12px] font-semibold transition-colors",
                freshness === option.value
                  ? "border-emerald bg-emerald/10 text-emerald-dark"
                  : "border-border bg-white text-muted hover:border-ink/20 hover:text-ink",
              )}
            >
              {option.label}
            </button>
          ))}
        </div>

        <SearchResultsToolbar
          running={running}
          total={total}
          shown={results.length}
          sort={sort}
          onSortChange={onSortChange}
          exportItems={exportItems}
          exportName="search"
          loading={searching}
          idleLabel="Натисніть «Шукати», щоб побачити авто за вашими фільтрами"
        />

        {error && (
          <div
            role="alert"
            className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] leading-relaxed text-red-700"
          >
            {error}
          </div>
        )}

        {searching ? (
          <SearchResultsSkeleton count={Math.min(SEARCH_PAGE_SIZE, 8)} />
        ) : !running ? (
          <div className="rounded-2xl border border-dashed border-border bg-surface/40 px-5 py-10 text-center sm:bg-white sm:px-6 sm:py-12">
            <p className="text-[15px] font-semibold text-ink">Результати з&apos;являться тут</p>
            <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-muted">
              Оберіть фільтри і натисніть «Шукати» — покажемо всі доступні авто по 20 з можливістю
              підвантажити ще.
            </p>
            <p className="mt-3 text-[11px] text-muted">
              До {SEARCH_HOURLY_LIMIT} запитів на годину
            </p>
          </div>
        ) : results.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white px-5 py-10 text-center sm:px-6 sm:py-12">
            <p className="text-[15px] font-semibold text-ink">За цими фільтрами поки нічого немає</p>
            <p className="mt-2 text-[13px] text-muted">
              {freshness === "new"
                ? "Спробуйте «Шукати всі» або збережіть моніторинг — сповістимо, коли зʼявиться нове."
                : "Збережіть пошук — ми повідомимо в Telegram, коли зʼявиться нова пропозиція."}
            </p>
          </div>
        ) : (
          <>
            <div className="-mx-1 flex flex-col gap-3 px-1 sm:mx-0 sm:gap-3 sm:px-0">
              {results.map(item => (
                <ListingCard
                  key={item.id}
                  listing={item}
                  onClick={() => openListing(item)}
                  isFavorite={favoriteIds.has(item.id)}
                  favoriteLoading={loadingIds.has(item.id)}
                  onToggleFavorite={() => toggleFavorite(item)}
                />
              ))}
            </div>

            {hasMore && onLoadMore && (
              <button
                type="button"
                onClick={onLoadMore}
                disabled={loadingMore}
                className="mt-6 w-full rounded-2xl border border-border bg-white py-3.5 text-[13px] font-semibold text-muted transition-colors hover:border-ink/20 hover:text-ink disabled:opacity-60"
              >
                {loadingMore ? "Завантаження..." : "Показати ще"}
              </button>
            )}

            {onSave && (
              <SearchPreviewNotice
                total={total}
                shown={results.length}
                freshness={freshness}
                onSave={onSave}
                saving={saving}
                telegramConnected={telegramConnected}
              />
            )}
          </>
        )}
      </div>

      <ListingDetailModal
        listing={selectedListing}
        onClose={() => {
          clearError();
          setSelectedListing(null);
        }}
        isFavorite={selectedListing ? favoriteIds.has(selectedListing.id) : false}
        favoriteLoading={selectedListing ? loadingIds.has(selectedListing.id) : false}
        onToggleFavorite={selectedListing ? () => toggleFavorite(selectedListing) : undefined}
        favoriteError={favoriteError}
      />
    </>
  );
}
