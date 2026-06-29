"use client";

import { useEffect, useMemo, useState } from "react";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
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
import { toBackendSearchFilters } from "@/lib/search-filters-api";
import type { Listing } from "@/types/api";
import type { ExportListing } from "@/lib/export-listings";

function toExportItems(items: Listing[]): ExportListing[] {
  return items.map(item => ({
    id: item.id,
    title: item.title,
    year: item.year,
    mileage: item.mileage,
    price: item.price,
    region: item.region,
    src: "AUTO.RIA",
    fuel: item.fuel,
    trans: item.transmission,
    desc: item.description ?? undefined,
    url: item.url,
  }));
}

export default function SearchPage() {
  const { user } = useAuth();
  const { saveSearch, saving, saveSuccess, saveError, saveLimitReached, clearSaveMessages } = useSaveSearch();
  const [filters, setFilters] = useState<SearchFilterState>({ ...DEFAULT_FILTERS });
  const [appliedFilters, setAppliedFilters] = useState<SearchFilterState | null>(null);
  const [results, setResults] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [sort, setSort] = useState<SortOption>("price_asc");
  const [running, setRunning] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);

  useEffect(() => {
    const draft = loadSearchDraft();
    if (draft) {
      setFilters(draft);
      clearSearchDraft();
    }
  }, []);

  const exportItems = useMemo(() => toExportItems(results), [results]);

  const runSearch = async (nextFilters: SearchFilterState, nextSort: SortOption) => {
    setSearching(true);
    setError(null);
    try {
      const data = await autoRia.search(toBackendSearchFilters(nextFilters), 1, 20, nextSort);
      setResults(data.items);
      setTotal(data.total);
      setAppliedFilters({ ...nextFilters });
      setRunning(true);
    } catch (err) {
      setResults([]);
      setTotal(0);
      setRunning(false);
      setError(err instanceof ApiError ? err.message : "Не вдалось виконати пошук на AUTO.RIA");
    } finally {
      setSearching(false);
    }
  };

  const handleSearch = () => {
    clearSaveMessages();
    void runSearch(filters, sort);
  };

  const handleReset = () => {
    clearSaveMessages();
    setFilters({ ...DEFAULT_FILTERS });
    setAppliedFilters(null);
    setResults([]);
    setTotal(0);
    setRunning(false);
    setSort("price_asc");
    setError(null);
  };

  const handleSortChange = (nextSort: SortOption) => {
    setSort(nextSort);
    if (appliedFilters) {
      void runSearch(appliedFilters, nextSort);
    }
  };

  const handleSave = () => {
    void saveSearch(filters);
  };

  const exportName = (appliedFilters?.name || filters.name || "poshuk").replace(/\s+/g, "-").toLowerCase();

  return (
    <div className="max-w-[1100px]">
      <div className="mb-5 flex flex-col gap-2 sm:mb-7 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
        <div>
          <h1 className="text-[22px] font-black tracking-[-0.02em] text-ink sm:text-[26px]">Пошук авто</h1>
          <p className="mt-1 text-[12px] text-muted sm:text-[13px]">
            Результати з{" "}
            <a
              href="https://auto.ria.com"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-emerald-dark hover:underline"
            >
              AUTO.RIA
            </a>
          </p>
        </div>
        <span className="w-fit rounded-lg border border-border bg-surface px-3 py-1.5 text-[11px] text-muted sm:bg-white sm:text-[12px]">
          Ліміт <strong className="text-ink">{user?.searches_limit ?? "—"}</strong> запитів
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

      <div className="mt-6 sm:mt-8">
        <SearchResultsToolbar
          running={running}
          total={total}
          shown={results.length}
          sort={sort}
          onSortChange={handleSortChange}
          exportItems={exportItems}
          exportName={exportName}
        />

        {error && (
          <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
            {error}
          </div>
        )}

        {!running ? (
          <div className="rounded-2xl border border-dashed border-border bg-surface/40 px-5 py-14 text-center sm:bg-white sm:px-6 sm:py-16">
            <p className="text-[15px] font-semibold text-ink">Оберіть фільтри і натисніть «Шукати»</p>
            <p className="mt-2 text-[13px] text-muted">Марка, модель, рік, ціна, регіон</p>
          </div>
        ) : results.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white px-5 py-14 text-center sm:px-6 sm:py-16">
            <p className="text-[15px] font-semibold text-ink">Нічого не знайдено</p>
            <p className="mt-2 text-[13px] text-muted">Спробуйте розширити діапазон року, ціни або змінити регіон</p>
          </div>
        ) : (
          <div className="-mx-1 flex flex-col gap-3 px-1 sm:mx-0 sm:gap-3 sm:px-0">
            {results.map(item => (
              <ListingCard
                key={item.id}
                listing={item}
                onClick={() => setSelectedListing(item)}
              />
            ))}
          </div>
        )}

        {running && results.length > 0 && (
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
          </p>
        )}
      </div>

      <ListingDetailModal listing={selectedListing} onClose={() => setSelectedListing(null)} />
    </div>
  );
}
