"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { SearchResultsToolbar } from "@/components/search/SearchResultsToolbar";
import { Button } from "@/components/ui/Button";
import { useListingFavorites } from "@/hooks/useListingFavorite";
import { useCompareOnListingCard } from "@/hooks/useCompareOnListingCard";
import { getApiErrorMessage, searches as searchesApi } from "@/lib/api";
import { notifyNotificationsChanged } from "@/lib/notifications-events";
import { formatSearchDesc } from "@/lib/format-search-desc";
import { saveRecentListing } from "@/lib/recent-listings";
import type { SortOption } from "@/lib/search-catalog";
import { listingsToExportItems } from "@/lib/export-listings";
import type { Listing, SearchQuery } from "@/types/api";
import { cn } from "@/lib/utils";

export default function MonitorDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: searchId } = use(params);
  const [search, setSearch] = useState<SearchQuery | null>(null);
  const [results, setResults] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [sort, setSort] = useState<SortOption>("newest");
  const [priceDropsOnly, setPriceDropsOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [newSeenFlash, setNewSeenFlash] = useState(0);
  const markedSeen = useRef(false);

  const loadResults = useCallback(
    async (
      id: string,
      nextPage: number,
      nextSort: SortOption,
      append: boolean,
      dropsOnly: boolean,
    ) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
        setError(null);
      }

      try {
        const data = await searchesApi.results(id, nextPage, 20, nextSort, {
          priceDropsOnly: dropsOnly,
        });
        setSearch(data.search);
        setTotal(data.results.total);
        setPages(data.results.pages);
        setPage(data.results.page);
        setResults(prev =>
          append ? [...prev, ...data.results.items] : data.results.items,
        );

        if (!append && !markedSeen.current && data.search.new_count > 0) {
          markedSeen.current = true;
          setNewSeenFlash(data.search.new_count);
          void searchesApi.markSeen(id).then(updated => {
            setSearch(updated);
            notifyNotificationsChanged();
          }).catch(() => {});
        }
      } catch (err) {
        if (!append) {
          setResults([]);
          setTotal(0);
          setSearch(null);
        }
        setError(getApiErrorMessage(err, "Не вдалось завантажити авто моніторингу"));
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [],
  );

  useEffect(() => {
    markedSeen.current = false;
    void loadResults(searchId, 1, sort, false, priceDropsOnly);
  }, [searchId, sort, priceDropsOnly, loadResults]);

  const exportItems = useMemo(() => listingsToExportItems(results), [results]);
  const exportName = (search?.name || "monitoring").replace(/\s+/g, "-").toLowerCase();
  const hasMore = page < pages;
  const {
    favoriteIds,
    loadingIds,
    error: favoriteError,
    clearError,
    toggleFavorite,
  } = useListingFavorites(results.map(item => item.id));
  const { cardCompareProps, compareHint } = useCompareOnListingCard();

  const openListing = (listing: Listing) => {
    saveRecentListing(listing);
    setSelectedListing(listing);
  };

  const handleSortChange = (nextSort: SortOption) => {
    setSort(nextSort);
    setPage(1);
  };

  const handlePriceDropsToggle = () => {
    setPriceDropsOnly(current => !current);
    setPage(1);
    if (!priceDropsOnly) {
      setSort("price_drop_desc");
    }
  };

  const handleLoadMore = () => {
    if (!hasMore || loadingMore) return;
    void loadResults(searchId, page + 1, sort, true, priceDropsOnly);
  };

  return (
    <div className="max-w-[860px] lg:max-w-none">
      <div className="mb-5 flex items-center gap-2 text-[12px] text-muted sm:mb-6">
        <Link href="/app/monitors" className="hover:text-ink">
          Мої моніторинги
        </Link>
        <span>/</span>
        <span className="truncate font-medium text-ink">
          {search?.name ?? "Завантаження..."}
        </span>
      </div>

      {search && (
        <p className="mb-5 text-[13px] text-muted">{formatSearchDesc(search.filters)}</p>
      )}

      {compareHint && (
        <div className="mb-4 rounded-xl bg-surface px-4 py-3 text-[13px] text-muted">{compareHint}</div>
      )}

      <SearchResultsToolbar
        running={!loading && !error && results.length > 0}
        total={total}
        shown={results.length}
        sort={sort}
        onSortChange={handleSortChange}
        exportItems={exportItems}
        exportName={exportName}
        isActive={search?.is_active}
        newCount={newSeenFlash || search?.new_count}
        priceDropCount={search?.price_drop_count}
        idleLabel={loading ? "Завантаження..." : "Немає авто в цьому моніторингу"}
      />

      {(search?.price_drop_count ?? 0) > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handlePriceDropsToggle}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12px] font-semibold transition-colors",
              priceDropsOnly
                ? "border-rose-300 bg-rose-50 text-rose-800"
                : "border-border bg-white text-muted hover:border-rose-200 hover:text-ink",
            )}
          >
            Зниження цін
            <span
              className={cn(
                "rounded-full px-1.5 py-0.5 text-[10px] font-bold",
                priceDropsOnly ? "bg-rose-600 text-white" : "bg-surface text-ink",
              )}
            >
              {search?.price_drop_count}
            </span>
          </button>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
        </div>
      ) : results.length === 0 && !error ? (
        <div className="rounded-2xl border border-border bg-white px-6 py-16 text-center">
          <p className="text-[15px] font-semibold text-ink">
            {priceDropsOnly ? "Немає знижень ціни" : "Поки порожньо"}
          </p>
          <p className="mt-2 text-[13px] text-muted">
            {priceDropsOnly
              ? "За вашими фільтрами поки немає авто зі значним зниженням (≥5%) за останні 14 днів."
              : "Збережіть моніторинг після першого пошуку — сюди потраплять показані авто і всі нові."}
          </p>
          <Link href="/app/dashboard" className="mt-6 flex justify-center">
            <Button variant="emerald" size="xl" className="w-full min-w-[min(100%,300px)] sm:w-auto sm:min-w-0">
              До пошуку
            </Button>
          </Link>
        </div>
      ) : (
        <div className="-mx-1 flex flex-col gap-3 px-1 sm:mx-0 sm:gap-3 sm:px-0 lg:gap-4">
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
      )}

      {hasMore && !loading && (
        <button
          type="button"
          onClick={handleLoadMore}
          disabled={loadingMore}
          className="mt-6 w-full rounded-2xl bg-emerald py-3.5 text-[14px] font-semibold text-white shadow-md shadow-emerald/25 transition-colors hover:bg-emerald-dark disabled:opacity-60"
        >
          {loadingMore ? "Завантаження..." : "Показати більше"}
        </button>
      )}

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
    </div>
  );
}
