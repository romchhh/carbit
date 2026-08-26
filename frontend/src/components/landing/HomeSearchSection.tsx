"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { useAuth } from "@/contexts/AuthProvider";
import {
  DEFAULT_FILTERS,
  normalizePriceRange,
  normalizeYearRange,
  type SearchFilterState,
} from "@/lib/search-catalog";
import { saveSearchDraft } from "@/lib/search-draft";
import type { SearchFreshness } from "@/lib/search-preview";
import { GUEST_SEARCH_LIMIT } from "@/lib/guest-search";

/** Дефолти для лендінгу: вся Україна, без попередньо заданої ціни. */
const HOME_DEFAULT_FILTERS: SearchFilterState = {
  ...DEFAULT_FILTERS,
  region: "Вся Україна",
  regions: [],
  currency: "USD",
};

export function HomeSearchSection() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [filters, setFilters] = useState<SearchFilterState>({ ...HOME_DEFAULT_FILTERS });
  const [freshness, setFreshness] = useState<SearchFreshness>("all");

  const handleReset = () => {
    setFilters({ ...HOME_DEFAULT_FILTERS });
    setFreshness("all");
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
    saveSearchDraft(sanitized, { freshness });
    router.push("/search");
  };

  return (
    <section id="search" className="scroll-mt-[72px] bg-white section-y sm:scroll-mt-[80px]">
      <div className="section-wrap">
        <div className="mb-10 sm:mb-12">
          <h2 className="text-[32px] font-bold leading-tight tracking-[-0.03em] text-ink sm:text-[40px]">
            Пошук і моніторинг авто
          </h2>
          <p className="mt-3 max-w-[560px] text-[16px] font-medium leading-relaxed text-ink/70 sm:mt-4 sm:text-[18px]">
            Оголошення з AUTO.RIA, OLX, Імперія Авто, uDrive і Telegram — оберіть фільтри й запускайте моніторинг
          </p>
          {!user && !loading ? (
            <p className="mt-3 inline-flex rounded-full border border-emerald/25 bg-emerald/10 px-3 py-1.5 text-[12px] font-semibold text-emerald-dark">
              {GUEST_SEARCH_LIMIT} безкоштовних пошуки без реєстрації
            </p>
          ) : null}
        </div>

        <SearchFiltersPanel
          wide
          voiceSearchCabinetOnly
          filters={filters}
          onChange={setFilters}
          onReset={handleReset}
          onSearch={handleSearch}
          freshness={freshness}
          onFreshnessChange={setFreshness}
          pricePlaceholderFrom="Від"
          pricePlaceholderTo="До"
        />
      </div>
    </section>
  );
}
