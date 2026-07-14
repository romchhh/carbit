"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { SearchResultsToolbar } from "@/components/search/SearchResultsToolbar";
import { useListingFavorites } from "@/hooks/useListingFavorite";
import { getApiErrorMessage, searches as searchesApi } from "@/lib/api";
import { saveRecentListing } from "@/lib/recent-listings";
import type { SortOption } from "@/lib/search-catalog";
import { listingsToExportItems } from "@/lib/export-listings";
import type { Listing, SearchQuery } from "@/types/api";

export default function ResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
        </div>
      }
    >
      <ResultsPageContent />
    </Suspense>
  );
}

function ResultsPageContent() {
  const searchParams = useSearchParams();
  const searchId = searchParams.get("search");

  const [search, setSearch] = useState<SearchQuery | null>(null);
  const [results, setResults] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [sort, setSort] = useState<SortOption>("newest");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);

  const loadResults = useCallback(
    async (id: string, nextPage: number, nextSort: SortOption, append: boolean) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
        setError(null);
      }

      try {
        const data = await searchesApi.results(id, nextPage, 20, nextSort);
        setSearch(data.search);
        setTotal(data.results.total);
        setPages(data.results.pages);
        setPage(data.results.page);
        setResults(prev =>
          append ? [...prev, ...data.results.items] : data.results.items,
        );
      } catch (err) {
        if (!append) {
          setResults([]);
          setTotal(0);
          setSearch(null);
        }
        setError(getApiErrorMessage(err, "Не вдалось завантажити результати"));
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!searchId) {
      setLoading(false);
      return;
    }
    void loadResults(searchId, 1, sort, false);
  }, [searchId, sort, loadResults]);

  const exportItems = useMemo(() => listingsToExportItems(results), [results]);
  const exportName = (search?.name || "rezultaty").replace(/\s+/g, "-").toLowerCase();
  const hasMore = page < pages;
  const { favoriteIds, loadingIds, error: favoriteError, clearError, toggleFavorite } = useListingFavorites(results.map(item => item.id));

  const openListing = (listing: Listing) => {
    saveRecentListing(listing);
    setSelectedListing(listing);
  };

  const handleSortChange = (nextSort: SortOption) => {
    setSort(nextSort);
    setPage(1);
  };

  const handleLoadMore = () => {
    if (!searchId || !hasMore || loadingMore) return;
    void loadResults(searchId, page + 1, sort, true);
  };

  if (!searchId) {
    return (
      <div className="max-w-[860px] rounded-2xl border border-dashed border-border bg-white px-6 py-16 text-center">
        <p className="text-[15px] font-semibold text-ink">Оберіть збережений пошук</p>
        <p className="mt-2 text-[13px] text-muted">Перейдіть до «Мої моніторинги» і відкрийте запит</p>
        <Link
          href="/app/monitors"
          className="mt-4 inline-flex rounded-full bg-emerald px-5 py-2.5 text-[13px] font-semibold text-white hover:bg-emerald-dark"
        >
          Мої моніторинги
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-[860px]">
      <div className="mb-5 flex items-center gap-2 text-[12px] text-muted sm:mb-6">
        <Link href="/app/monitors" className="hover:text-ink">
          Мої моніторинги
        </Link>
        <span>/</span>
        <span className="truncate font-medium text-ink">
          {search?.name ?? "Завантаження..."}
        </span>
      </div>

      <SearchResultsToolbar
        running={!loading && !error && results.length > 0}
        total={total}
        shown={results.length}
        sort={sort}
        onSortChange={handleSortChange}
        exportItems={exportItems}
        exportName={exportName}
        isActive={search?.is_active}
        newCount={search?.new_count}
        idleLabel={loading ? "Завантаження..." : "Немає результатів"}
      />

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
          <p className="text-[15px] font-semibold text-ink">Нічого не знайдено</p>
          <p className="mt-2 text-[13px] text-muted">
            Спробуйте змінити фільтри збереженого пошуку або перевірте пізніше
          </p>
        </div>
      ) : (
        <div className="-mx-1 flex flex-col gap-3 px-1 sm:mx-0 sm:px-0">
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
      )}

      {hasMore && !loading && (
        <button
          type="button"
          onClick={handleLoadMore}
          disabled={loadingMore}
          className="mt-6 w-full rounded-2xl border border-border bg-white py-3.5 text-[13px] font-semibold text-muted transition-colors hover:border-ink/20 hover:text-ink disabled:opacity-60"
        >
          {loadingMore ? "Завантаження..." : "Показати більше результатів"}
        </button>
      )}

      {results.length > 0 && (
        <p className="mt-4 pb-1 text-center text-[11px] text-muted">
          Дані надано{" "}
          <a
            href="https://auto.ria.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-emerald-dark hover:underline"
          >
            AUTO.RIA
          </a>
          {" "}та{" "}
          <a
            href="https://www.olx.ua"
            target="_blank"
            rel="noopener noreferrer"
            className="text-emerald-dark hover:underline"
          >
            OLX
          </a>
        </p>
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
