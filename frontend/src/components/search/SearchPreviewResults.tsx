"use client";

import { useMemo, useState } from "react";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { SearchPreviewNotice } from "@/components/search/SearchPreviewNotice";
import { SearchResultsSkeleton } from "@/components/search/SearchResultsSkeleton";
import { SearchResultsToolbar } from "@/components/search/SearchResultsToolbar";
import { useListingFavorites } from "@/hooks/useListingFavorite";
import { saveRecentListing } from "@/lib/recent-listings";
import { PREVIEW_HOURLY_LIMIT, PREVIEW_RESULTS_LIMIT } from "@/lib/search-preview";
import type { Listing } from "@/types/api";

type Props = {
  resultsRef: React.RefObject<HTMLDivElement | null>;
  running: boolean;
  searching: boolean;
  total: number;
  results: Listing[];
  error?: string | null;
  onSave?: () => void;
  saving?: boolean;
  telegramConnected?: boolean;
};

export function SearchPreviewResults({
  resultsRef,
  running,
  searching,
  total,
  results,
  error,
  onSave,
  saving,
  telegramConnected,
}: Props) {
  const previewResults = useMemo(
    () => results.slice(0, PREVIEW_RESULTS_LIMIT),
    [results],
  );
  const { favoriteIds, loadingIds, toggleFavorite } = useListingFavorites(
    previewResults.map(item => item.id),
  );
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);

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
          shown={previewResults.length}
          sort="price_asc"
          onSortChange={() => {}}
          exportItems={[]}
          exportName="preview"
          loading={searching}
          previewMode
          previewLimit={PREVIEW_RESULTS_LIMIT}
          idleLabel="Натисніть «Шукати», щоб побачити кілька прикладів"
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
          <SearchResultsSkeleton count={PREVIEW_RESULTS_LIMIT} />
        ) : !running ? (
          <div className="rounded-2xl border border-dashed border-border bg-surface/40 px-5 py-10 text-center sm:bg-white sm:px-6 sm:py-12">
            <p className="text-[15px] font-semibold text-ink">Приклади з&apos;являться тут</p>
            <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-muted">
              Оберіть фільтри і натисніть «Шукати» — покажемо до {PREVIEW_RESULTS_LIMIT} авто з AUTO.RIA.
            </p>
            <p className="mt-3 text-[11px] text-muted">
              До {PREVIEW_HOURLY_LIMIT} переглядів на годину
            </p>
          </div>
        ) : previewResults.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white px-5 py-10 text-center sm:px-6 sm:py-12">
            <p className="text-[15px] font-semibold text-ink">За цими фільтрами поки нічого немає</p>
            <p className="mt-2 text-[13px] text-muted">
              Збережіть пошук — ми повідомимо в Telegram, коли з&apos;явиться нова пропозиція
            </p>
          </div>
        ) : (
          <>
            <div className="-mx-1 flex flex-col gap-3 px-1 sm:mx-0 sm:gap-3 sm:px-0">
              {previewResults.map(item => (
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

            {onSave && (
              <SearchPreviewNotice
                total={total}
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
        onClose={() => setSelectedListing(null)}
        isFavorite={selectedListing ? favoriteIds.has(selectedListing.id) : false}
        favoriteLoading={selectedListing ? loadingIds.has(selectedListing.id) : false}
        onToggleFavorite={selectedListing ? () => toggleFavorite(selectedListing) : undefined}
      />
    </>
  );
}
