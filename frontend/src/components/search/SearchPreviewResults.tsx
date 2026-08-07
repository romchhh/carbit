"use client";

import { useMemo, useState } from "react";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { SearchProgressBar } from "@/components/search/SearchProgressBar";
import { SearchResultsSkeleton } from "@/components/search/SearchResultsSkeleton";
import { SearchResultsToolbar } from "@/components/search/SearchResultsToolbar";
import { useListingFavorites } from "@/hooks/useListingFavorite";
import { useCompareOnListingCard } from "@/hooks/useCompareOnListingCard";
import { saveRecentListing } from "@/lib/recent-listings";
import type { SortOption } from "@/lib/search-catalog";
import { listingsToExportItems } from "@/lib/export-listings";
import { SEARCH_PAGE_SIZE, type SearchFreshness } from "@/lib/search-preview";
import { flavorForLoadMore, flavorForRefresh } from "@/lib/search-flavor";
import { isSearchRateLimitMessage } from "@/components/search/SearchRateLimitNotice";
import type { Listing, SourceStatus } from "@/types/api";
import { cn } from "@/lib/utils";

function sourceLabel(source: string): string {
  if (source === "olx" || source === "OLX") return "OLX";
  if (source === "auto_ria" || source === "AUTO.RIA") return "AUTO.RIA";
  if (source === "telegram" || source === "Telegram") return "Telegram";
  return source.toUpperCase();
}

function isOlxSource(source: string): boolean {
  return source === "olx" || source === "OLX";
}

/** Зрозуміле повідомлення про збій джерела замість «креативних» текстів. */
function sourceFailureMessage(status: SourceStatus): string {
  const label = sourceLabel(status.source);
  const raw = (status.error || "").trim();

  if (isOlxSource(status.source)) {
    if (/обмежує|429|rate/i.test(raw)) {
      return "OLX тимчасово обмежує запити. Показуємо результати з інших джерел.";
    }
    if (/timeout|час очікування|timed?\s*out/i.test(raw)) {
      return "OLX не відповів вчасно. Показуємо результати з інших джерел.";
    }
    return "OLX тимчасово недоступний. Показуємо результати з інших джерел.";
  }

  if (raw && raw.length < 120 && !/Error|Exception|Traceback|HTTP/i.test(raw)) {
    return `${label}: ${raw}`;
  }
  return `${label} тимчасово недоступний. Показуємо результати з інших джерел.`;
}

function buildPartialHint(
  statuses: SourceStatus[] | undefined,
  partial: boolean | undefined,
  fromCache: boolean | undefined,
): string | null {
  if (!partial) return null;
  const failed = (statuses ?? []).filter(s => s.error);
  if (failed.length === 0) return null;

  const lines = failed.map(sourceFailureMessage);
  if (fromCache) {
    lines.push("Частина результатів з кешу.");
  }
  return lines.join(" ");
}

type Props = {
  resultsRef: React.RefObject<HTMLDivElement | null>;
  running: boolean;
  searching: boolean;
  loadingMore?: boolean;
  hasMore?: boolean;
  total: number;
  marketTotal?: number | null;
  results: Listing[];
  sort: SortOption;
  freshness: SearchFreshness;
  error?: string | null;
  sourceStatuses?: SourceStatus[];
  partial?: boolean;
  fromCache?: boolean;
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
  marketTotal,
  results,
  sort,
  freshness,
  error,
  sourceStatuses,
  partial,
  fromCache,
  onSortChange,
  onLoadMore,
}: Props) {
  const { favoriteIds, loadingIds, error: favoriteError, clearError, toggleFavorite } = useListingFavorites(
    results.map(item => item.id),
  );
  const { cardCompareProps, compareHint } = useCompareOnListingCard();
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const exportItems = useMemo(() => listingsToExportItems(results), [results]);
  const remaining = Math.max(0, total - results.length);
  const nextBatch = Math.min(SEARCH_PAGE_SIZE, remaining);

  const partialHint = buildPartialHint(sourceStatuses, partial, fromCache);
  const loadMoreLabel = useMemo(() => flavorForLoadMore(results.length), [results.length]);
  const refreshLabel = useMemo(() => flavorForRefresh(total), [total]);

  const rawTotal = marketTotal ?? total;
  const displayTotal = rawTotal > 80 ? rawTotal + 10 : rawTotal;

  const openListing = (listing: Listing) => {
    saveRecentListing(listing);
    setSelectedListing(listing);
  };

  return (
    <>
      <div ref={resultsRef} id="search-results" className="mt-6 scroll-mt-28 sm:mt-8 sm:scroll-mt-24">
        {running && (
          <SearchResultsToolbar
            running={running}
            total={displayTotal}
            shown={results.length}
            sort={sort}
            onSortChange={onSortChange}
            exportItems={exportItems}
            exportName="search"
          />
        )}

        {error && !isSearchRateLimitMessage(error) && (
          <div
            role="alert"
            className="mb-4 rounded-2xl border border-border/80 bg-surface/70 px-4 py-3 text-[13px] leading-relaxed text-muted"
          >
            <span className="font-medium text-ink/80">{error}</span>
          </div>
        )}

        {partialHint && !error && (
          <div
            role="status"
            className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] leading-relaxed text-amber-900"
          >
            {partialHint}
          </div>
        )}

        {compareHint && (
          <div
            role="status"
            className="mb-4 rounded-2xl border border-border/80 bg-surface/70 px-4 py-3 text-[13px] text-muted"
          >
            {compareHint}
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
              На підписці — більше пошуків на годину, ніж на безкоштовному тарифі
            </p>
          </div>
        ) : results.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white px-5 py-10 text-center sm:px-6 sm:py-12">
            <p className="text-[15px] font-semibold text-ink">На цьому ряду порожньо</p>
            <p className="mt-2 text-[13px] text-muted">
              {freshness === "new"
                ? "Зніміть «Тільки свіжі» або змініть фільтри."
                : "Спробуйте розширити фільтри — рік, ціну чи регіон."}
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
                  onClick={() => openListing(item)}
                  isFavorite={favoriteIds.has(item.id)}
                  favoriteLoading={loadingIds.has(item.id)}
                  onToggleFavorite={() => toggleFavorite(item)}
                  {...cardCompareProps(item)}
                />
              ))}
            </div>

            {hasMore && onLoadMore && (
              <button
                type="button"
                onClick={onLoadMore}
                disabled={loadingMore || searching}
                className="mt-6 w-full rounded-2xl border border-border bg-white py-3.5 text-[14px] font-semibold text-ink transition-colors hover:bg-surface disabled:opacity-60"
              >
                {loadingMore ? (
                  "Завантаження…"
                ) : (
                  <span className="inline-flex items-center justify-center gap-1.5">
                    <span>Показати ще</span>
                    {nextBatch > 0 && (
                      <span className="font-bold text-ink">+{nextBatch}</span>
                    )}
                    {displayTotal > 0 && (
                      <span className="font-medium text-muted">
                        · {results.length} з {displayTotal.toLocaleString("uk-UA")}
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
