"use client";

import { useState } from "react";
import { AdvancedSearchPanel } from "@/components/search/AdvancedSearchPanel";
import { FilterOptionsPopover } from "@/components/search/FilterOptionsPopover";
import { FilterRangePopover } from "@/components/search/FilterRangePopover";
import { cn } from "@/lib/utils";
import { BRANDS, getModelsForBrand } from "@/lib/search-data/brands-models";
import { UKRAINE_REGIONS } from "@/lib/search-data/regions";
import {
  CATEGORY_OPTIONS,
  DEFAULT_FILTERS,
  VEHICLE_TYPE_OPTIONS,
  type SearchFilterState,
} from "@/lib/search-catalog";

type Props = {
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
  onReset: () => void;
  onSearch: () => void;
  searching?: boolean;
  wide?: boolean;
};

export function SearchFiltersPanel({ filters, onChange, onReset, onSearch, searching, wide }: Props) {
  const [advanced, setAdvanced] = useState(false);
  const models = filters.brand ? getModelsForBrand(filters.brand) : [];

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

  return (
    <div className={cn("w-full", wide ? "max-w-none" : "max-w-[640px]")}>
      <div className="overflow-hidden rounded-[1.35rem] border border-border/80 bg-white shadow-[0_8px_30px_-12px_rgba(10,12,14,0.18)] ring-1 ring-black/[0.04]">
        <div className="border-b border-border/60 bg-surface/70 px-4 py-3.5 sm:px-5">
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

        <div className="space-y-2 bg-surface/40 px-4 py-4 sm:px-5 sm:py-5">
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
            <p className="px-1 text-[12px] text-muted">
              Обрано: <span className="font-medium text-ink">{brandModelLabel || "—"}</span>
            </p>
          )}

          <FilterRangePopover
            label="Рік випуску"
            from={filters.yearFrom}
            to={filters.yearTo}
            onChange={(yearFrom, yearTo) => update({ yearFrom, yearTo })}
            format={v => v.replace(/[^\d]/g, "").slice(0, 4)}
            placeholderFrom={DEFAULT_FILTERS.yearFrom}
            placeholderTo={DEFAULT_FILTERS.yearTo}
          />

          <FilterOptionsPopover
            label="Регіон"
            value={filters.region === "Вся Україна" ? "" : filters.region}
            options={[...UKRAINE_REGIONS.filter(r => r !== "Вся Україна")]}
            onChange={region => update({ region: region || "Вся Україна" })}
            searchable
            emptyLabel="Вся Україна"
          />
        </div>

        <div className="space-y-2 border-t border-border/60 bg-white px-4 py-4 sm:px-5">
          <button
            type="button"
            onClick={onSearch}
            disabled={searching}
            className="w-full rounded-full bg-emerald py-3.5 text-[16px] font-semibold text-white shadow-md shadow-emerald/25 transition-colors hover:bg-emerald-dark disabled:opacity-60"
          >
            {searching ? "Шукаємо..." : "Шукати"}
          </button>
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
    </div>
  );
}
