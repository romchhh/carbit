"use client";

import { useState } from "react";
import { AdvancedSearchPanel } from "@/components/search/AdvancedSearchPanel";
import { BrandIcon } from "@/components/search/BrandIcon";
import { FilterOptionsPopover } from "@/components/search/FilterOptionsPopover";
import { FilterRangePopover } from "@/components/search/FilterRangePopover";
import { SaveSearchCTA } from "@/components/search/SaveSearchCTA";
import {
  SearchRateLimitNotice,
  isSearchRateLimitMessage,
} from "@/components/search/SearchRateLimitNotice";
import { IosToggle } from "@/components/ui/IosToggle";
import { cn } from "@/lib/utils";
import { getBrandIconUrl } from "@/lib/search-data/brand-icons";
import { BRANDS, getModelsForBrand } from "@/lib/search-data/brands-models";
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
} from "@/lib/search-catalog";
import type { SearchFreshness } from "@/lib/search-preview";
import { resolveDisplayCurrency, type DisplayCurrency } from "@/lib/display-currency";

type Props = {
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
  onReset: () => void;
  searchButtonLabel?: string;
  searchingButtonLabel?: string;
  searchError?: string | null;
  searchErrorRetryAfter?: number | null;
  onSearch: () => void;
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
  freshness = "all",
  onFreshnessChange,
}: Props) {
  const [advanced, setAdvanced] = useState(false);
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

  const brandModelLabel =
    filters.brand && filters.model
      ? `${filters.brand} ${filters.model}`
      : filters.brand || "";

  const selectedBrandIcon = filters.brand ? getBrandIconUrl(filters.brand) : null;

  return (
    <div className={cn("w-full", wide ? "max-w-none" : "max-w-[640px]")} data-tour="search-filters">
      <div className="rounded-[1.35rem] border border-border/80 bg-white shadow-[0_8px_30px_-12px_rgba(10,12,14,0.18)] ring-1 ring-black/[0.04] transition-shadow duration-300">
        <div className="overflow-hidden rounded-t-[1.35rem] border-b border-border/60 bg-surface/70 px-3 py-3.5 sm:px-5">
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
            />
            <FilterOptionsPopover
              label="Модель"
              value={filters.model}
              options={models}
              onChange={model => update({ model })}
              searchable
              emptyLabel="Будь-яка модель"
              disabled={!filters.brand}
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
              placeholderFrom={DEFAULT_PRICE_BY_CURRENCY[filters.currency].from}
              placeholderTo={DEFAULT_PRICE_BY_CURRENCY[filters.currency].to}
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

      <div className="mt-4 space-y-3 rounded-[1.35rem] border border-border/80 bg-white px-3 py-3.5 shadow-[0_8px_30px_-12px_rgba(10,12,14,0.18)] ring-1 ring-black/[0.04] sm:px-5">
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
          onClick={onSearch}
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
  );
}
