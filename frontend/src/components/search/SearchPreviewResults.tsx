"use client";

import { useMemo, useState } from "react";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { SearchProgressBar } from "@/components/search/SearchProgressBar";
import { SearchResultsSkeleton } from "@/components/search/SearchResultsSkeleton";
import { SearchResultsToolbar } from "@/components/search/SearchResultsToolbar";
import { useListingFavorites } from "@/hooks/useListingFavorite";
import { saveRecentListing } from "@/lib/recent-listings";
import type { SortOption } from "@/lib/search-catalog";
import type { ExportListing } from "@/lib/export-listings";
import { SEARCH_HOURLY_LIMIT, SEARCH_PAGE_SIZE, type SearchFreshness } from "@/lib/search-preview";
import {
  flavorForLoadMore,
  flavorForPartial,
  flavorForRefresh,
} from "@/lib/search-flavor";
import type { DisplayCurrency } from "@/lib/display-currency";
import type { Listing, SourceStatus } from "@/types/api";
import { cn } from "@/lib/utils";

function sourceLabel(source: string): string {
  if (source === "olx" || source === "OLX") return "OLX";
  if (source === "auto_ria" || source === "AUTO.RIA") return "AUTO.RIA";
  if (source === "telegram" || source === "Telegram") return "Telegram";
  return source.toUpperCase();
}

function toExportItems(items: Listing[]): ExportListing[] {
  return items.map(item => ({
    id: item.id,
    title: item.title,
    year: item.year,
    mileage: item.mileage,
    price: item.price,
    currency: item.currency,
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
  sourceStatuses?: SourceStatus[];
  partial?: boolean;
  fromCache?: boolean;
  displayCurrency?: DisplayCurrency;
  onSortChange: (sort: SortOption) => void;
  onFreshnessChange: (freshness: SearchFreshness) => void;
  onLoadMore?: () => void;
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
  sourceStatuses,
  partial,
  fromCache,
  displayCurrency = "USD",
  onSortChange,
  onLoadMore,
}: Props) {
  const { favoriteIds, loadingIds, error: favoriteError, clearError, toggleFavorite } = useListingFavorites(
    results.map(item => item.id),
  );
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const exportItems = useMemo(() => toExportItems(results), [results]);
  const remaining = Math.max(0, total - results.length);
  const nextBatch = Math.min(SEARCH_PAGE_SIZE, remaining);

  const pendingSources = (sourceStatuses ?? []).filter(s => s.error);
  const pendingKey = pendingSources.map(s => s.source).join("|");
  const partialLine = useMemo(() => flavorForPartial(pendingKey.length + total), [pendingKey, total]);
  const loadMoreLabel = useMemo(() => flavorForLoadMore(results.length), [results.length]);
  const refreshLabel = useMemo(() => flavorForRefresh(total), [total]);

  const partialHint =
    partial && pendingSources.length > 0
      ? `${partialLine} (${pendingSources.map(s => sourceLabel(s.source)).join(", ")})`
      : null;

  const openListing = (listing: Listing) => {
    saveRecentListing(listing);
    setSelectedListing(listing);
  };

  return (
    <>
      <div ref={resultsRef} className="mt-6 scroll-mt-24 sm:mt-8">
        <SearchResultsToolbar
          running={running}
          total={total}
          shown={results.length}
          sort={sort}
          onSortChange={onSortChange}
          exportItems={exportItems}
          exportName="search"
          loading={searching}
          idleLabel="Натисніть «Шукати» — підемо гуляти авторинками за вас"
        />

        {error && (
          <div
            role="alert"
            className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] leading-relaxed text-red-700"
          >
            {error}
          </div>
        )}

        {partialHint && !error && (
          <div
            role="status"
            className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] leading-relaxed text-amber-900"
          >
            {partialHint}
            {fromCache ? " Трохи підглянули в свіжий кеш, щоб не ганяти зайве." : ""}
          </div>
        )}

        <SearchProgressBar
          active={searching || Boolean(loadingMore)}
          compact={false}
          label={
            loadingMore
              ? loadMoreLabel
              : searching && running
                ? refreshLabel
                : undefined
          }
          hint={loadingMore ? null : undefined}
          className="mb-4"
        />

        {searching && !running ? (
          <SearchResultsSkeleton count={3} />
        ) : !running ? (
          <div className="rounded-2xl border border-dashed border-border bg-surface/40 px-5 py-10 text-center sm:bg-white sm:px-6 sm:py-12">
            <p className="text-[15px] font-semibold text-ink">Авторинок ще порожній</p>
            <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-muted">
              Оберіть фільтри і тисніть «Шукати» — обійдемо AUTO.RIA, OLX і Telegram,
              ніби це один великий автобазар.
            </p>
            <p className="mt-3 text-[11px] text-muted">
              До {SEARCH_HOURLY_LIMIT} прогулянок ринком на годину — ноги теж втомлюються
            </p>
          </div>
        ) : results.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white px-5 py-10 text-center sm:px-6 sm:py-12">
            <p className="text-[15px] font-semibold text-ink">На цьому ряду порожньо</p>
            <p className="mt-2 text-[13px] text-muted">
              {freshness === "new"
                ? "Оберіть «Усі пропозиції» або підключіть моніторинг — свиснемо, коли з’явиться нове."
                : "Підключіть моніторинг — напишемо в Telegram, щойно хтось виставить цікаве."}
            </p>
          </div>
        ) : (
          <>
            <div
              className={cn(
                "relative -mx-1 flex flex-col gap-3 px-1 sm:mx-0 sm:gap-3 sm:px-0",
                searching && "opacity-70",
              )}
              aria-busy={searching || loadingMore}
            >
              {searching && (
                <div
                  role="status"
                  className="sticky top-16 z-10 mb-1 rounded-xl border border-emerald/25 bg-white/95 px-3 py-2 text-center text-[12px] font-medium text-emerald-dark shadow-sm backdrop-blur-sm"
                >
                  Ще шукаємо на ринку — сторінку можна гортати
                </div>
              )}
              {results.map(item => (
                <ListingCard
                  key={item.id}
                  listing={item}
                  displayCurrency={displayCurrency}
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
                disabled={loadingMore || searching}
                className="mt-6 w-full rounded-2xl bg-emerald py-3.5 text-[14px] font-semibold text-white shadow-md shadow-emerald/25 transition-colors hover:bg-emerald-dark disabled:opacity-60"
              >
                {loadingMore ? (
                  "Завантаження…"
                ) : (
                  <span className="inline-flex items-center justify-center gap-1.5">
                    <span>Показати ще</span>
                    {nextBatch > 0 && (
                      <span className="font-bold">+{nextBatch}</span>
                    )}
                    {total > 0 && (
                      <span className="font-medium text-white/80">
                        · {results.length} з {total.toLocaleString("uk-UA")}
                      </span>
                    )}
                  </span>
                )}
              </button>
            )}
          </>
        )}
      </div>

      <ListingDetailModal
        listing={selectedListing}
        displayCurrency={displayCurrency}
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
