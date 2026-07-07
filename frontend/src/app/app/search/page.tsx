"use client";

import { useEffect } from "react";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { SearchPreviewResults } from "@/components/search/SearchPreviewResults";
import { useAuth } from "@/contexts/AuthProvider";
import { usePreviewSearch } from "@/hooks/usePreviewSearch";
import { useSaveSearch } from "@/hooks/useSaveSearch";
import { RecentListingsSection } from "@/components/listings/RecentListingsSection";
import { clearSearchDraft, loadSearchDraft } from "@/lib/search-draft";

export default function SearchPage() {
  const { user } = useAuth();
  const { saveSearch, saving, saveSuccess, saveError, saveLimitReached, clearSaveMessages } = useSaveSearch();
  const {
    filters,
    setFilters,
    results,
    total,
    running,
    searching,
    error,
    resultsRef,
    runSearch,
    reset,
    clearError,
  } = usePreviewSearch();

  useEffect(() => {
    const draft = loadSearchDraft();
    if (!draft) return;
    clearSearchDraft();
    void runSearch(draft);
  }, [runSearch]);

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
    <div className="max-w-[1100px]">
      <RecentListingsSection className="mb-8" />
      <div className="mb-5 flex flex-col gap-2 sm:mb-7 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
        <div>
          <h1 className="text-[22px] font-black tracking-[-0.02em] text-ink sm:text-[26px]">
            Пошук авто
          </h1>
          <p className="mt-1 max-w-[560px] text-[12px] leading-relaxed text-muted sm:text-[13px]">
            AUTO.RIA та OLX в одному місці. Налаштуйте фільтри, перегляньте кілька прикладів і
            збережіть пошук — Carbit надсилатиме <strong className="font-medium text-ink">нові</strong>{" "}
            авто за цими параметрами прямо в Telegram.
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
          searchError={error}
          saving={saving}
          saveSuccess={saveSuccess}
          saveError={saveError}
          saveLimitReached={saveLimitReached}
          telegramConnected={user?.telegram_connected}
        />
      </div>

      <SearchPreviewResults
        resultsRef={resultsRef}
        running={running}
        searching={searching}
        total={total}
        results={results}
        onSave={handleSave}
        saving={saving}
        telegramConnected={user?.telegram_connected}
      />
    </div>
  );
}
