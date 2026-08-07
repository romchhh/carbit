"use client";

import { useRef, useState } from "react";
import { AdvancedSearchPanel } from "@/components/search/AdvancedSearchPanel";
import { BrandIcon } from "@/components/search/BrandIcon";
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
import { mergeAiSearchFilters } from "@/lib/search-filters-api";
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
  freshness?: SearchFreshness;
  onFreshnessChange?: (freshness: SearchFreshness) => void;
  /** Плейсхолдери поля ціни (на лендінгу — без заготовленого діапазону). */
  pricePlaceholderFrom?: string;
  pricePlaceholderTo?: string;
  /** На лендінгу — кнопка «Голосом» лише показує підказку про кабінет. */
  voiceSearchCabinetOnly?: boolean;
  onSortChange?: (sort: SortOption) => void;
};

function mergeVoiceFilters(
  current: SearchFilterState,
  raw: Record<string, unknown>,
  result: AiParseSearchResult,
): SearchFilterState {
  const merged = mergeAiSearchFilters(current, raw);
  const hasRegion = raw.region != null && String(raw.region).trim();
  if (!hasRegion) {
    merged.region = "Вся Україна";
  }
  if (isMarketDiscoveryResult(result) && !raw.brand) {
    merged.brand = "";
    merged.model = "";
  }
  return merged;
}

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
  const models = filters.brand ? getModelsForBrand(filters.brand) : [];
  const rateLimited = isSearchRateLimitMessage(searchError);

  const update = (patch: Partial<SearchFilterState>) => {
    onChange({ ...filters, ...patch });
  };

  const handleBrandChange = (brand: string) => {
    const nextModels = brand ? getModelsForBrand(brand) : [];
    update({
      brand,
      model: brand && nextModels.includes(filters.model) ? filters.model : "",
    });
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
    const merged = mergeVoiceFilters(filters, raw, result);
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
    onChange(nextFilters);

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

  const brandModelLabel =
    filters.brand && filters.model
      ? `${filters.brand} ${filters.model}`
      : filters.brand || "";

  const selectedBrandIcon = filters.brand ? getBrandIconUrl(filters.brand) : null;

  return (
    <>
      <div className={cn("w-full", wide ? "max-w-none" : "max-w-[640px]")} data-tour="search-filters">
        <div className="rounded-[1.35rem] border border-border/80 bg-white shadow-[0_8px_30px_-12px_rgba(10,12,14,0.18)] ring-1 ring-black/[0.04] transition-shadow duration-300">
          <div className="overflow-hidden rounded-t-[1.35rem] border-b border-border/60 bg-surface/70 px-3 py-3.5 sm:px-5">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div className="min-w-0 pt-1">
                <p className="text-[13px] font-semibold text-ink">Категорія</p>
                <p className="mt-0.5 hidden text-[11px] text-muted sm:block">
                  {voiceSearchCabinetOnly
                    ? "Голосовий пошук — у кабінеті після входу"
                    : "Або скажіть голосом — AI заповнить фільтри"}
                </p>
              </div>
              <VoiceSearchTrigger onClick={handleVoiceClick} />
            </div>
            <div className="overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              <div className="flex min-w-max gap-2">
                {CATEGORY_OPTIONS.map(({ value, label }) => {
                  const active = filters.category === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => update({ category: value })}
                      className={cn(
                        "rounded-full border px-4 py-2 text-[14px] font-medium whitespace-nowrap transition-colors",
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

          <div className="relative z-20 space-y-2 bg-surface/40 px-3 py-3.5 sm:px-5 sm:py-5">
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
            />

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <FilterOptionsPopover
                label="Марка"
                value={filters.brand}
                options={BRANDS}
                onChange={handleBrandChange}
                searchable
                emptyLabel="Будь-яка марка"
                getOptionIcon={getBrandIconUrl}
                filterOptionsFn={(opts, q) => filterBrandOptions(opts, q)}
                resolveQueryFn={q => resolveBrandQuery(q, BRANDS)}
              />
              <FilterOptionsPopover
                label="Модель"
                value={filters.model}
                options={models}
                onChange={model => update({ model })}
                searchable
                emptyLabel="Будь-яка модель"
                disabled={!filters.brand}
                filterOptionsFn={(opts, q) =>
                  filters.brand ? filterModelOptions(filters.brand, opts, q) : []
                }
                resolveQueryFn={q =>
                  filters.brand ? resolveModelQuery(filters.brand, q, models) : null
                }
              />
            </div>

            {(filters.brand || filters.model) && (
              <p className="flex items-center gap-2 px-1 text-[12px] text-muted">
                {selectedBrandIcon && <BrandIcon src={selectedBrandIcon} size={18} />}
                <span>
                  Обрано:{" "}
                  <span className="font-medium text-ink">{brandModelLabel || "—"}</span>
                </span>
              </p>
            )}

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
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
              />
            </div>

            <FilterOptionsPopover
              label="Регіон"
              value={
                !filters.region || filters.region === "Вся Україна"
                  ? "Всі регіони"
                  : filters.region
              }
              options={[...UKRAINE_REGIONS.filter(r => r !== "Вся Україна")]}
              onChange={region =>
                update({
                  region:
                    !region || region === "Всі регіони" ? "Вся Україна" : region,
                })
              }
              searchable
              emptyLabel="Всі регіони"
            />
          </div>

          <div className="relative z-10 space-y-2 overflow-hidden rounded-b-[1.35rem] border-t border-border/60 bg-white px-3 py-3.5 sm:px-5">
            <button
              type="button"
              onClick={() => setAdvanced(v => !v)}
              className="w-full rounded-full border border-border bg-surface py-3.5 text-[16px] font-semibold text-ink transition-colors hover:border-ink/20 hover:bg-surface/80"
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
          className="mt-4 scroll-mt-28 space-y-3 rounded-[1.35rem] border border-border/80 bg-white px-3 py-3.5 shadow-[0_8px_30px_-12px_rgba(10,12,14,0.18)] ring-1 ring-black/[0.04] sm:scroll-mt-8 sm:px-5 lg:scroll-mt-6"
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
              "relative w-full overflow-hidden rounded-full bg-emerald py-3.5 text-[16px] font-semibold text-white shadow-md shadow-emerald/25 transition-all duration-300 hover:bg-emerald-dark disabled:cursor-wait",
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
