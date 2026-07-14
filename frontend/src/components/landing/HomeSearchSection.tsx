"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AuthGateModal } from "@/components/auth/AuthGateModal";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { useAuth } from "@/contexts/AuthProvider";
import { DEFAULT_FILTERS, normalizePriceRange, normalizeYearRange, type SearchFilterState } from "@/lib/search-catalog";
import { saveSearchDraft } from "@/lib/search-draft";
import type { SearchFreshness } from "@/lib/search-preview";

export function HomeSearchSection() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [filters, setFilters] = useState<SearchFilterState>({ ...DEFAULT_FILTERS });
  const [freshness, setFreshness] = useState<SearchFreshness>("new");
  const [authOpen, setAuthOpen] = useState(false);

  const handleReset = () => {
    setFilters({ ...DEFAULT_FILTERS });
    setFreshness("new");
  };

  const handleSearch = () => {
    const years = normalizeYearRange(filters.yearFrom, filters.yearTo);
    const prices = normalizePriceRange(filters.priceFrom, filters.priceTo);
    const sanitized = {
      ...filters,
      yearFrom: years.from,
      yearTo: years.to,
      priceFrom: prices.from,
      priceTo: prices.to,
    };
    setFilters(sanitized);
    saveSearchDraft(sanitized);

    if (user) {
      router.push("/app/search");
      return;
    }

    setAuthOpen(true);
  };

  const handleAuthenticated = () => {
    setAuthOpen(false);
    router.push("/app/search");
  };

  return (
    <>
      <section id="search" className="scroll-mt-[72px] bg-white section-y sm:scroll-mt-[80px]">
        <div className="section-wrap">
          <div className="mb-10 sm:mb-12">
            <h2 className="text-[32px] font-bold leading-tight tracking-[-0.03em] text-ink sm:text-[40px]">
              Моніторинг авто
            </h2>
            <p className="mt-3 max-w-[560px] text-[16px] font-medium leading-relaxed text-ink/70 sm:mt-4 sm:text-[18px]">
              Оберіть фільтри — Carbit відстежуватиме нові оголошення на AUTO.RIA і надсилатиме їх у Telegram
            </p>
          </div>

          <SearchFiltersPanel
            wide
            filters={filters}
            onChange={setFilters}
            onReset={handleReset}
            onSearch={handleSearch}
            freshness={freshness}
            onFreshnessChange={setFreshness}
          />
        </div>
      </section>

      {!loading && (
        <AuthGateModal
          open={authOpen}
          onClose={() => setAuthOpen(false)}
          onAuthenticated={handleAuthenticated}
        />
      )}
    </>
  );
}
