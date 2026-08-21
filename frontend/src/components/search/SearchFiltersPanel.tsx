"use client";

import { useRef, useState } from "react";
import { AdvancedSearchPanel } from "@/components/search/AdvancedSearchPanel";
import { FilterOptionsPopover } from "@/components/search/FilterOptionsPopover";
import { FilterRangePopover } from "@/components/search/FilterRangePopover";
import { SaveSearchCTA } from "@/components/search/SaveSearchCTA";
import { VoiceSearchCabinetOnlyOverlay } from "@/components/search/VoiceSearchCabinetOnlyOverlay";
import { VoiceSearchOverlay } from "@/components/search/VoiceSearchOverlay";
import { VoiceSearchTrigger } from "@/components/search/VoiceSearchTrigger";
import {
  SearchRateLimitNotice,
  isSearchRateLimitMessage,
} from "@/components/search/SearchRateLimitNotice";
import { IosToggle } from "@/components/ui/IosToggle";
import { cn } from "@/lib/utils";
import { getBrandIconUrl } from "@/lib/search-data/brand-icons";
import { BRANDS, getModelsForBrand } from "@/lib/search-data/brands-models";
import {
  filterBrandOptions,
  filterModelOptions,
  findBrandInText,
  findModelInText,
  resolveBrandQuery,
  resolveModelQuery,
} from "@/lib/search-data/brand-model-resolve";
import { UKRAINE_REGIONS } from "@/lib/search-data/regions";
import {
  CATEGORY_OPTIONS,
  DEFAULT_PRICE_BY_CURRENCY,
  PRICE_CURRENCY_OPTIONS,
  VEHICLE_TYPE_OPTIONS,
  YEAR_MIN,
  YEAR_PLACEHOLDERS,
  formatPriceInput,
  formatYearInput,
  normalizePriceRange,
  normalizeYearRange,
  yearMax,
  type SearchFilterState,
  type SortOption,
} from "@/lib/search-catalog";
import type { SearchFreshness } from "@/lib/search-preview";
import { resolveDisplayCurrency, type DisplayCurrency } from "@/lib/display-currency";
import { applyVoiceSearchFilters } from "@/lib/search-filters-api";
import { syncSearchFilterArrays } from "@/lib/search-filter-multi";
import { isMarketDiscoveryResult } from "@/lib/voice-search-summary";
import type { AiParseSearchResult } from "@/lib/api";

type Props = {
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
  onReset: () => void;
  searchButtonLabel?: string;
  searchingButtonLabel?: string;
  searchError?: string | null;
  searchErrorRetryAfter?: number | null;
  onSearch: (overrideFilters?: SearchFilterState, overrideSort?: SortOption) => void;
  onSave?: () => void;
  searching?: boolean;
  saving?: boolean;
  saveSuccess?: string | null;
  saveError?: string | null;
  saveLimitReached?: boolean;
  telegramConnected?: boolean;
  monitorConnected?: boolean;
  connectedMonitorId?: string | null;
  wide?: boolean;
  /** Компактна ліва колонка на desktop (як AUTO.RIA). */
  variant?: "default" | "sidebar";
  /** На desktop моніторинг — fixed-кнопка, блок CTA ховаємо. */
  hideDesktopSave?: boolean;
  freshness?: SearchFreshness;
  onFreshnessChange?: (freshness: SearchFreshness) => void;
  /** Плейсхолдери поля ціни (на лендінгу — без заготовленого діапазону). */
  pricePlaceholderFrom?: string;
  pricePlaceholderTo?: string;
  /** На лендінгу — кнопка «Голосом» лише показує підказку про кабінет. */
  voiceSearchCabinetOnly?: boolean;
  onSortChange?: (sort: SortOption) => void;
};

export function SearchFiltersPanel({
  filters,
  onChange,
  onReset,
  onSearch,
  onSave,
  searching,
  searchButtonLabel = "Шукати",
  searchingButtonLabel = "На ринку…",
  saving,
  saveSuccess,
  saveError,
  saveLimitReached,
  searchError,
  searchErrorRetryAfter,
  telegramConnected,
  monitorConnected,
  connectedMonitorId,
  wide,
  variant = "default",
  hideDesktopSave,
  freshness = "all",
  onFreshnessChange,
  pricePlaceholderFrom,
  pricePlaceholderTo,
  voiceSearchCabinetOnly,
  onSortChange,
}: Props) {
  const priceDefaults = DEFAULT_PRICE_BY_CURRENCY[filters.currency];
  const priceFromPlaceholder = pricePlaceholderFrom ?? priceDefaults.from;
  const priceToPlaceholder = pricePlaceholderTo ?? priceDefaults.to;
  const [advanced, setAdvanced] = useState(false);
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [voiceCabinetOnlyOpen, setVoiceCabinetOnlyOpen] = useState(false);
  const [voiceHint, setVoiceHint] = useState<string | null>(null);
  const searchActionsRef = useRef<HTMLDivElement>(null);
  const syncedFilters = syncSearchFilterArrays(filters);
  const rateLimited = isSearchRateLimitMessage(searchError);
  const sidebar = variant === "sidebar";
  const compactFilters = sidebar;

  const applyFilters = (next: SearchFilterState) => {
    onChange(syncSearchFilterArrays(next));
  };

  const update = (patch: Partial<SearchFilterState>) => {
    applyFilters({ ...syncSearchFilterArrays(filters), ...patch });
  };

  const scrollToSearch = () => {
    window.requestAnimationFrame(() => {
      window.setTimeout(() => {
        searchActionsRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }, 150);
    });
  };

  const handleVoiceClick = () => {
    if (voiceSearchCabinetOnly) {
      setVoiceCabinetOnlyOpen(true);
      return;
    }
    setVoiceOpen(true);
  };

  const handleVoiceApplied = (
    raw: Record<string, unknown>,
    result: AiParseSearchResult,
    searchNow = false,
  ) => {
    const merged = applyVoiceSearchFilters(filters, raw, {
      transcript: result.transcript,
      marketDiscovery: isMarketDiscoveryResult(result),
      resolveBrand: query => resolveBrandQuery(query, BRANDS),
      resolveModel: (brand, query) =>
        resolveModelQuery(brand, query, getModelsForBrand(brand)),
      findBrandInText: text => findBrandInText(text, BRANDS),
      findModelInText: (brand, text) =>
        findModelInText(brand, text, getModelsForBrand(brand)),
    });
    const years = normalizeYearRange(merged.yearFrom, merged.yearTo);
    const prices = normalizePriceRange(merged.priceFrom, merged.priceTo);
    const marketDiscovery = isMarketDiscoveryResult(result);
    const nextFilters = {
      ...merged,
      yearFrom: years.from,
      yearTo: years.to,
      priceFrom: prices.from,
      priceTo: prices.to,
    };
    onChange(syncSearchFilterArrays(nextFilters));

    if (result.sort) {
      onSortChange?.(result.sort);
    }

    setVoiceHint(
      result.message ||
        (marketDiscovery
          ? "Шукаю найкращі варіанти по ринку…"
          : "Фільтри заповнено — натисніть «Шукати»."),
    );
    window.setTimeout(() => setVoiceHint(null), 6000);
    scrollToSearch();

    if (searchNow) {
      window.setTimeout(
        () => onSearch(nextFilters, result.sort ?? undefined),
        100,
      );
    }
  };

  return (
    <>
      <div
        className={cn(
          "w-full",
          wide ? "max-w-none" : "max-w-[640px]",
          variant === "sidebar" && "lg:max-w-none",
        )}
        data-tour="search-filters"
      >
        <div
          className={cn(
            "rounded-[1.35rem] border border-border/80 bg-white shadow-[0_8px_30px_-12px_rgba(10,12,14,0.18)] ring-1 ring-black/[0.04] transition-shadow duration-300",
            variant === "sidebar" &&
              "lg:rounded-2xl lg:shadow-[0_4px_20px_-10px_rgba(10,12,14,0.15)]",
          )}
        >
          <div
            className={cn(
              "overflow-hidden rounded-t-[1.35rem] border-b border-border/60 bg-surface/70 px-3 py-3.5 sm:px-5",
              sidebar && "lg:rounded-t-2xl lg:px-3.5 lg:py-3",
            )}
          >
            <div className={cn("mb-3 flex items-start justify-between gap-2", sidebar && "lg:mb-2")}>
              <div className="min-w-0 pt-0.5">
                <p className={cn("font-semibold text-ink", sidebar ? "text-[12px]" : "text-[13px]")}>
                  Категорія
                </p>
                <p
                  className={cn(
                    "mt-0.5 hidden text-[11px] text-muted sm:block",
                    sidebar && "lg:hidden",
                  )}
                >
                  {voiceSearchCabinetOnly
                    ? "Голосовий пошук — у кабінеті після входу"
                    : "Або скажіть голосом — AI заповнить фільтри"}
                </p>
              </div>
              <VoiceSearchTrigger onClick={handleVoiceClick} compact={compactFilters} />
            </div>
            <div
              className={cn(
                "overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
                sidebar && "lg:overflow-visible",
              )}
            >
              <div
                className={cn(
                  "flex min-w-max gap-2",
                  sidebar && "lg:min-w-0 lg:flex-wrap lg:gap-1.5",
                )}
              >
                {CATEGORY_OPTIONS.map(({ value, label }) => {
                  const active = filters.category === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => update({ category: value })}
                      className={cn(
                        "rounded-full border font-medium whitespace-nowrap transition-colors",
                        sidebar
                          ? "px-2.5 py-1.5 text-[12px] lg:px-3"
                          : "px-4 py-2 text-[14px]",
                        active
                          ? "border-ink bg-ink text-white shadow-sm"
                          : "border-border bg-white text-ink hover:border-emerald/40",
                      )}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div
            className={cn(
              "relative z-20 space-y-2 bg-surface/40 px-3 py-3.5 sm:px-5 sm:py-5",
              sidebar && "lg:space-y-1.5 lg:px-3.5 lg:py-3",
            )}
          >
            {voiceHint && (
              <div className="flex items-start gap-3 rounded-2xl border border-emerald/20 bg-gradient-to-r from-emerald/10 to-cyan-500/5 px-3.5 py-3">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-emerald/15 text-emerald-dark">
                  ✓
                </span>
                <p className="text-[13px] leading-relaxed text-emerald-dark">{voiceHint}</p>
              </div>
            )}

            <FilterOptionsPopover
              label="Тип транспорту"
              value={filters.vehicleType}
              options={[...VEHICLE_TYPE_OPTIONS]}
              onChange={vehicleType => update({ vehicleType })}
              compact={compactFilters}
            />

            <div
              className={cn(
                "grid grid-cols-1 gap-2 sm:grid-cols-2",
                sidebar && "lg:grid-cols-1 lg:gap-1.5",
              )}
            >
              <FilterOptionsPopover
                label="Марка"
                value={syncedFilters.brand}
                options={BRANDS}
                onChange={brand =>
                  applyFilters({
                    ...syncedFilters,
                    brand,
                    model: "",
                    brands: brand ? [brand] : [],
                    models: [],
                  })
                }
                searchable
                emptyLabel="Будь-яка марка"
                getOptionIcon={getBrandIconUrl}
                filterOptionsFn={(opts, q) => filterBrandOptions(opts, q)}
                resolveQueryFn={q => resolveBrandQuery(q, BRANDS)}
                compact={compactFilters}
              />
              <FilterOptionsPopover
                label="Модель"
                value={syncedFilters.model}
                options={syncedFilters.brand ? getModelsForBrand(syncedFilters.brand) : []}
                onChange={model =>
                  applyFilters({
                    ...syncedFilters,
                    model,
                    models: model ? [model] : [],
                  })
                }
                searchable
                emptyLabel="Будь-яка модель"
                disabled={!syncedFilters.brand}
                filterOptionsFn={(opts, q) =>
                  filterModelOptions(syncedFilters.brand, opts, q)
                }
                resolveQueryFn={q =>
                  resolveModelQuery(syncedFilters.brand, q, getModelsForBrand(syncedFilters.brand))
                }
                compact={compactFilters}
              />
            </div>

            <div
              className={cn(
                "grid grid-cols-1 gap-2 sm:grid-cols-2",
                sidebar && "lg:grid-cols-1 lg:gap-1.5",
              )}
            >
              <FilterRangePopover
                label="Рік випуску"
                from={filters.yearFrom}
                to={filters.yearTo}
                onChange={(yearFrom, yearTo) => update({ yearFrom, yearTo })}
                format={formatYearInput}
                normalize={normalizeYearRange}
                hint={`Допустимо ${YEAR_MIN}–${yearMax()}.`}
                placeholderFrom={YEAR_PLACEHOLDERS.from}
                placeholderTo={YEAR_PLACEHOLDERS.to}
                compact={compactFilters}
              />
              <FilterRangePopover
                label="Ціна"
                from={filters.priceFrom}
                to={filters.priceTo}
                onChange={(priceFrom, priceTo) => update({ priceFrom, priceTo })}
                format={formatPriceInput}
                normalize={normalizePriceRange}
                placeholderFrom={priceFromPlaceholder}
                placeholderTo={priceToPlaceholder}
                suffix={
                  filters.currency === "USD" ? "$" : filters.currency === "EUR" ? "€" : "грн"
                }
                currency={filters.currency}
                currencyOptions={PRICE_CURRENCY_OPTIONS.map(option => ({
                  value: option.value,
                  label: option.label,
                }))}
                onCurrencyChange={value => {
                  const next = resolveDisplayCurrency(value) as DisplayCurrency;
                  update({
                    currency: next,
                    priceFrom: "",
                    priceTo: "",
                  });
                }}
                compact={compactFilters}
              />
            </div>

            <FilterOptionsPopover
              label="Регіон"
              value={syncedFilters.region === "Вся Україна" ? "" : syncedFilters.region}
              options={[...UKRAINE_REGIONS.filter(r => r !== "Вся Україна")]}
              onChange={region =>
                applyFilters({
                  ...syncedFilters,
                  region: region || "Вся Україна",
                  regions: region ? [region] : [],
                })
              }
              searchable
              emptyLabel="Вся Україна"
              compact={compactFilters}
            />

          </div>

          <div
            className={cn(
              "relative z-10 space-y-2 overflow-hidden rounded-b-[1.35rem] border-t border-border/60 bg-white px-3 py-3.5 sm:px-5",
              sidebar && "lg:rounded-b-2xl lg:px-3.5 lg:py-3",
            )}
          >
            <button
              type="button"
              onClick={() => setAdvanced(v => !v)}
              className={cn(
                "w-full rounded-full border border-border bg-surface font-semibold text-ink transition-colors hover:border-ink/20 hover:bg-surface/80",
                sidebar ? "py-2.5 text-[13px]" : "py-3.5 text-[16px]",
              )}
            >
              {advanced ? "Сховати розширений пошук" : "Розширений пошук"}
            </button>
          </div>
        </div>

        {advanced && (
          <AdvancedSearchPanel filters={filters} onChange={onChange} onReset={onReset} />
        )}

        <div
          ref={searchActionsRef}
          className={cn(
            "mt-4 scroll-mt-28 space-y-3 rounded-[1.35rem] border border-border/80 bg-white px-3 py-3.5 shadow-[0_8px_30px_-12px_rgba(10,12,14,0.18)] ring-1 ring-black/[0.04] sm:scroll-mt-8 sm:px-5 lg:scroll-mt-6",
            sidebar &&
              "lg:mt-3 lg:space-y-2 lg:rounded-2xl lg:px-3.5 lg:py-3 lg:shadow-[0_4px_20px_-10px_rgba(10,12,14,0.15)]",
          )}
        >
          {rateLimited ? (
            <SearchRateLimitNotice
              message={searchError}
              retryAfterSeconds={searchErrorRetryAfter}
            />
          ) : searchError ? (
            <div
              role="alert"
              className="rounded-xl border border-border/80 bg-surface/70 px-3.5 py-3 text-[13px] leading-relaxed text-muted"
            >
              <span className="font-medium text-ink/80">{searchError}</span>
            </div>
          ) : null}
          <button
            type="button"
            onClick={() => onSearch()}
            disabled={searching}
            className={cn(
              "relative w-full overflow-hidden rounded-full bg-emerald font-semibold text-white shadow-md shadow-emerald/25 transition-all duration-300 hover:bg-emerald-dark disabled:cursor-wait",
              sidebar ? "py-2.5 text-[14px]" : "py-3.5 text-[16px]",
              searching && "animate-pulse shadow-[0_0_0_4px_rgba(16,185,129,0.25)]",
            )}
          >
            <span className={cn("inline-flex items-center justify-center gap-2", searching && "opacity-90")}>
              {searching && (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              )}
              {searching ? searchingButtonLabel : searchButtonLabel}
            </span>
          </button>

          {onFreshnessChange && (
            <div className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-white px-3.5 py-3">
              <span className="text-[13px] font-semibold text-ink">Тільки свіжі оголошення</span>
              <IosToggle
                checked={freshness === "new"}
                disabled={searching}
                aria-label="Тільки свіжі оголошення"
                onChange={checked => onFreshnessChange(checked ? "new" : "all")}
              />
            </div>
          )}

          {onSave && (
            <SaveSearchCTA
              className={cn(hideDesktopSave && "lg:hidden")}
              onSave={onSave}
              saving={saving}
              successMessage={saveSuccess}
              errorMessage={saveError}
              limitReached={saveLimitReached}
              telegramConnected={telegramConnected}
              monitorConnected={monitorConnected}
              connectedMonitorId={connectedMonitorId}
              hideSubscriptionPitch={rateLimited}
            />
          )}
        </div>
      </div>

      {voiceSearchCabinetOnly ? (
        <VoiceSearchCabinetOnlyOverlay
          open={voiceCabinetOnlyOpen}
          onClose={() => setVoiceCabinetOnlyOpen(false)}
        />
      ) : (
        <VoiceSearchOverlay
          open={voiceOpen}
          onClose={() => setVoiceOpen(false)}
          onApplied={handleVoiceApplied}
        />
      )}
    </>
  );
}
