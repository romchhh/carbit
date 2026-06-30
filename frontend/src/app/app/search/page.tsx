"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { SearchPreviewNotice } from "@/components/search/SearchPreviewNotice";
import { SearchResultsSkeleton } from "@/components/search/SearchResultsSkeleton";
import { SearchResultsToolbar } from "@/components/search/SearchResultsToolbar";
import { useAuth } from "@/contexts/AuthProvider";
import { useSaveSearch } from "@/hooks/useSaveSearch";
import { ApiError, autoRia } from "@/lib/api";
import {
  DEFAULT_FILTERS,
  type SearchFilterState,
  type SortOption,
} from "@/lib/search-catalog";
import { clearSearchDraft, loadSearchDraft } from "@/lib/search-draft";
import { useListingFavorites } from "@/hooks/useListingFavorite";
import { RecentListingsSection } from "@/components/listings/RecentListingsSection";
import { saveRecentListing } from "@/lib/recent-listings";
import { PREVIEW_HOURLY_LIMIT, PREVIEW_RESULTS_LIMIT } from "@/lib/search-preview";
import { toBackendSearchFilters } from "@/lib/search-filters-api";
import type { Listing } from "@/types/api";

export default function SearchPage() {
  const resultsRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();
  const { saveSearch, saving, saveSuccess, saveError, saveLimitReached, clearSaveMessages } = useSaveSearch();
  const [filters, setFilters] = useState<SearchFilterState>({ ...DEFAULT_FILTERS });
  const [appliedFilters, setAppliedFilters] = useState<SearchFilterState | null>(null);
  const [results, setResults] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [sort] = useState<SortOption>("price_asc");
  const [running, setRunning] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);

  const runSearch = async (nextFilters: SearchFilterState) => {
    setSearching(true);
    setError(null);
    resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const data = await autoRia.search(
        toBackendSearchFilters(nextFilters),
        1,
        PREVIEW_RESULTS_LIMIT,
        "price_asc",
        "preview",
      );
      setResults(data.items.slice(0, PREVIEW_RESULTS_LIMIT));
      setTotal(data.total);
      setAppliedFilters({ ...nextFilters });
      setRunning(true);
    } catch (err) {
      setResults([]);
      setTotal(0);
      setRunning(false);
      setError(err instanceof ApiError ? err.message : "Не вдалось переглянути приклади на AUTO.RIA");
    } finally {
      setSearching(false);
    }
  };

  useEffect(() => {
    const draft = loadSearchDraft();
    if (!draft) return;

    setFilters(draft);
    clearSearchDraft();

    void (async () => {
      setSearching(true);
      setError(null);
      requestAnimationFrame(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      try {
        const data = await autoRia.search(
          toBackendSearchFilters(draft),
          1,
          PREVIEW_RESULTS_LIMIT,
          "price_asc",
          "preview",
        );
        setResults(data.items.slice(0, PREVIEW_RESULTS_LIMIT));
        setTotal(data.total);
        setAppliedFilters({ ...draft });
        setRunning(true);
      } catch (err) {
        setResults([]);
        setTotal(0);
        setRunning(false);
        setError(err instanceof ApiError ? err.message : "Не вдалось переглянути приклади на AUTO.RIA");
      } finally {
        setSearching(false);
      }
    })();
  }, []);

  const handleSearch = () => {
    clearSaveMessages();
    void runSearch(filters);
  };

  const handleReset = () => {
    clearSaveMessages();
    setFilters({ ...DEFAULT_FILTERS });
    setAppliedFilters(null);
    setResults([]);
    setTotal(0);
    setRunning(false);
    setError(null);
  };

  const handleSave = () => {
    void saveSearch(filters);
  };

  const previewResults = useMemo(
    () => results.slice(0, PREVIEW_RESULTS_LIMIT),
    [results],
  );
  const { favoriteIds, loadingIds, toggleFavorite } = useListingFavorites(previewResults.map(item => item.id));

  const openListing = (listing: Listing) => {
    saveRecentListing(listing);
    setSelectedListing(listing);
  };

  return (
    <div className="max-w-[1100px]">
      <RecentListingsSection className="mb-8" />
      <div className="mb-5 flex flex-col gap-2 sm:mb-7 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
        <div>
          <h1 className="text-[22px] font-black tracking-[-0.02em] text-ink sm:text-[26px]">
            Моніторинг AUTO.RIA
          </h1>
          <p className="mt-1 max-w-[560px] text-[12px] leading-relaxed text-muted sm:text-[13px]">
            Налаштуйте фільтри, перегляньте кілька прикладів і збережіть пошук — Carbit
            надсилатиме <strong className="font-medium text-ink">нові</strong> авто за цими
            параметрами прямо в Telegram.
          </p>
        </div>
        <span className="w-fit rounded-lg border border-border bg-surface px-3 py-1.5 text-[11px] text-muted sm:bg-white sm:text-[12px]">
          До <strong className="text-ink">{user?.searches_limit ?? "—"}</strong> збережених
          моніторингів
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
          saving={saving}
          saveSuccess={saveSuccess}
          saveError={saveError}
          saveLimitReached={saveLimitReached}
          telegramConnected={user?.telegram_connected}
        />
      </div>

      <div ref={resultsRef} className="mt-6 scroll-mt-24 sm:mt-8">
        <SearchResultsToolbar
          running={running}
          total={total}
          shown={previewResults.length}
          sort={sort}
          onSortChange={() => {}}
          exportItems={[]}
          exportName="preview"
          loading={searching}
          previewMode
          previewLimit={PREVIEW_RESULTS_LIMIT}
          idleLabel="Натисніть «Шукати», щоб побачити кілька прикладів"
        />

        {error && (
          <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
            {error}
          </div>
        )}

        {searching ? (
          <SearchResultsSkeleton count={PREVIEW_RESULTS_LIMIT} />
        ) : !running ? (
          <div className="rounded-2xl border border-dashed border-border bg-surface/40 px-5 py-14 text-center sm:bg-white sm:px-6 sm:py-16">
            <p className="text-[15px] font-semibold text-ink">Це не каталог усіх авто</p>
            <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-muted">
              Оберіть фільтри і перегляньте до {PREVIEW_RESULTS_LIMIT} прикладів.
              Повний потік нових пропозицій — після збереження пошуку в Telegram.
            </p>
            <p className="mt-3 text-[11px] text-muted">
              До {PREVIEW_HOURLY_LIMIT} переглядів на годину
            </p>
          </div>
        ) : previewResults.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white px-5 py-14 text-center sm:px-6 sm:py-16">
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

            <SearchPreviewNotice
              total={total}
              onSave={handleSave}
              saving={saving}
              telegramConnected={user?.telegram_connected}
            />
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
    </div>
  );
}
