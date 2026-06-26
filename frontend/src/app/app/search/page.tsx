"use client";

import { useMemo, useState } from "react";
import { IconArrowRight } from "@/components/icons";
import { Badge } from "@/components/ui/Badge";
import { ExportMenu } from "@/components/search/ExportMenu";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { useAuth } from "@/contexts/AuthProvider";
import { cn } from "@/lib/utils";
import {
  CATALOG_LISTINGS,
  DEFAULT_FILTERS,
  filterListings,
  sortListings,
  type SearchFilterState,
  type SortOption,
} from "@/lib/search-catalog";

const riskLabel: Record<string, { label: string; color: string }> = {
  low: { label: "Брати", color: "text-emerald-dark bg-emerald-light" },
  medium: { label: "Торгуватись", color: "text-yellow-700 bg-yellow-50" },
  high: { label: "Пропустити", color: "text-red-600 bg-red-50" },
};

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "price_asc", label: "Спочатку дешеві" },
  { value: "price_desc", label: "Спочатку дорогі" },
  { value: "year_desc", label: "Спочатку нові" },
  { value: "mileage_asc", label: "За пробігом" },
];

export default function SearchPage() {
  const { user } = useAuth();
  const [filters, setFilters] = useState<SearchFilterState>({
    ...DEFAULT_FILTERS,
    name: "Camry під перепродаж",
    brand: "Toyota",
    model: "Camry",
    region: "м. Київ",
  });
  const [appliedFilters, setAppliedFilters] = useState<SearchFilterState | null>(null);
  const [sort, setSort] = useState<SortOption>("price_asc");
  const [running, setRunning] = useState(false);
  const [searching, setSearching] = useState(false);

  const results = useMemo(() => {
    if (!appliedFilters) return [];
    return sortListings(filterListings(CATALOG_LISTINGS, appliedFilters), sort);
  }, [appliedFilters, sort]);

  const handleSearch = () => {
    setSearching(true);
    window.setTimeout(() => {
      setAppliedFilters({ ...filters });
      setRunning(true);
      setSearching(false);
    }, 350);
  };

  const handleReset = () => {
    setFilters({ ...DEFAULT_FILTERS });
    setAppliedFilters(null);
    setRunning(false);
    setSort("price_asc");
  };

  const exportName = (appliedFilters?.name || filters.name || "poshuk").replace(/\s+/g, "-").toLowerCase();

  return (
    <div className="max-w-[1100px]">
      <div className="mb-7 flex items-start justify-between">
        <div>
          <h1 className="text-[26px] font-black tracking-[-0.02em] text-ink">Новий запит</h1>
          <p className="mt-1 text-[13px] text-muted">Налаштуй фільтри — Carbit шукатиме автоматично</p>
        </div>
        <span className="rounded-lg border border-border bg-white px-3 py-1.5 text-[12px] text-muted">
          Ліміт тарифу <strong className="text-ink">{user?.searches_limit ?? "—"}</strong> запитів
        </span>
      </div>

      <div className="flex items-start gap-6">
        <SearchFiltersPanel
          filters={filters}
          onChange={setFilters}
          onReset={handleReset}
          onSearch={handleSearch}
          searching={searching}
        />

        <div className="min-w-0 flex-1">
          <div className="mb-4 flex items-center justify-between rounded-xl border border-border bg-white px-5 py-3.5">
            <div className="flex items-center gap-3 text-[13px]">
              {running ? (
                <span className="flex items-center gap-2 font-medium text-emerald-dark">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald" />
                  Пошук активний
                </span>
              ) : (
                <span className="text-muted">Запустіть пошук</span>
              )}
              {running && (
                <>
                  <span className="text-border">·</span>
                  <span className="text-muted">
                    Знайдено <strong className="text-ink">{results.length}</strong>
                  </span>
                </>
              )}
            </div>
            {running && (
              <div className="flex items-center gap-3">
                <ExportMenu items={results} filename={exportName} />
                <select
                  value={sort}
                  onChange={e => setSort(e.target.value as SortOption)}
                  className="rounded-lg border border-border bg-white px-3 py-1.5 text-[12px] text-muted focus:outline-none"
                >
                  {SORT_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {!running ? (
            <div className="rounded-xl border border-dashed border-border bg-white px-6 py-16 text-center">
              <p className="text-[15px] font-semibold text-ink">Оберіть фільтри і натисніть «Запустити пошук»</p>
              <p className="mt-2 text-[13px] text-muted">Марка, модель, регіон, ціна, двигун, КПП та джерела</p>
            </div>
          ) : results.length === 0 ? (
            <div className="rounded-xl border border-border bg-white px-6 py-16 text-center">
              <p className="text-[15px] font-semibold text-ink">Нічого не знайдено</p>
              <p className="mt-2 text-[13px] text-muted">Спробуйте розширити діапазон року, ціни або змінити регіон</p>
            </div>
          ) : (
            <div className="space-y-3">
              {results.map(r => {
                const risk = riskLabel[r.risk];
                return (
                  <article
                    key={r.id}
                    className="flex cursor-pointer gap-4 rounded-xl border border-border bg-white p-4 transition-colors hover:border-ink/15"
                  >
                    <div className="flex h-32 w-48 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-surface">
                      <svg width="40" height="40" viewBox="0 0 28 28" fill="none" className="opacity-10">
                        <rect x="12.5" y="0" width="3" height="28" fill="#0A0C0E" />
                        <rect x="0" y="12.5" width="28" height="3" fill="#0A0C0E" />
                      </svg>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="text-[15px] font-bold text-ink">{r.title}</h3>
                          <p className="mt-0.5 text-[12px] text-muted">
                            {r.year} · {r.mileage.toLocaleString("uk-UA")} км · {r.trans} · {r.fuel} · {r.region}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="text-[20px] font-black leading-none text-ink">{r.price.toLocaleString("uk-UA")}</div>
                          <div className="text-[11px] text-muted">грн</div>
                        </div>
                      </div>
                      <p className="mt-2.5 line-clamp-1 text-[12px] leading-relaxed text-muted">{r.desc}</p>
                      <div className="mt-3 flex items-center gap-3">
                        <span className={cn("rounded px-2 py-0.5 text-[11px] font-bold", risk.color)}>{risk.label}</span>
                        <Badge variant="outline">{r.src}</Badge>
                        <span className="text-[11px] text-muted">{r.time}</span>
                        <span className="ml-auto flex items-center gap-1 text-[12px] font-semibold text-emerald-dark hover:underline">
                          Детальніше <IconArrowRight size={11} />
                        </span>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
