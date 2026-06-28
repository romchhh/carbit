"use client";

import { useState } from "react";
import { FilterOptionsPopover } from "@/components/search/FilterOptionsPopover";
import { FilterRangePopover } from "@/components/search/FilterRangePopover";
import { cn } from "@/lib/utils";
import { BRANDS, getModelsForBrand } from "@/lib/search-data/brands-models";
import { UKRAINE_REGIONS } from "@/lib/search-data/regions";
import {
  CATEGORY_OPTIONS,
  DEFAULT_FILTERS,
  FUEL_OPTIONS,
  SOURCE_OPTIONS,
  TRANSMISSION_OPTIONS,
  VEHICLE_TYPE_OPTIONS,
  formatPriceInput,
  toggleValue,
  type SearchFilterState,
} from "@/lib/search-catalog";

type Props = {
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
  onReset: () => void;
  onSearch: () => void;
  searching?: boolean;
};

export function SearchFiltersPanel({ filters, onChange, onReset, onSearch, searching }: Props) {
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
    <div className="w-full max-w-[640px]">
      <div className="overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
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
                    ? "border-ink bg-ink text-white"
                    : "border-border bg-white text-ink hover:border-emerald/40",
                )}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-3 space-y-2">
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

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <FilterRangePopover
            label="Рік випуску"
            from={filters.yearFrom}
            to={filters.yearTo}
            onChange={(yearFrom, yearTo) => update({ yearFrom, yearTo })}
            format={v => v.replace(/[^\d]/g, "").slice(0, 4)}
            placeholderFrom={DEFAULT_FILTERS.yearFrom}
            placeholderTo={DEFAULT_FILTERS.yearTo}
          />
          <FilterRangePopover
            label="Вартість"
            from={filters.priceFrom}
            to={filters.priceTo}
            onChange={(priceFrom, priceTo) => update({ priceFrom, priceTo })}
            format={formatPriceInput}
            placeholderFrom="400 000"
            placeholderTo="900 000"
            suffix="грн"
          />
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <FilterOptionsPopover
            label="Регіон"
            value={filters.region === "Вся Україна" ? "" : filters.region}
            options={[...UKRAINE_REGIONS.filter(r => r !== "Вся Україна")]}
            onChange={region => update({ region: region || "Вся Україна" })}
            searchable
            emptyLabel="Вся Україна"
          />
          <FilterOptionsPopover
            label="Пальне"
            value=""
            values={filters.fuels}
            options={[...FUEL_OPTIONS]}
            onChange={() => {}}
            onToggle={fuel => update({ fuels: toggleValue(filters.fuels, fuel) })}
            multiple
          />
        </div>

        <FilterOptionsPopover
          label="Коробка передач"
          value=""
          values={filters.transmissions}
          options={[...TRANSMISSION_OPTIONS]}
          onChange={() => {}}
          onToggle={trans => update({ transmissions: toggleValue(filters.transmissions, trans) })}
          multiple
        />
      </div>

      <div className="mt-4 space-y-2">
        <button
          type="button"
          onClick={onSearch}
          disabled={searching}
          className="w-full rounded-full bg-emerald py-3.5 text-[16px] font-semibold text-white transition-colors hover:bg-emerald-dark disabled:opacity-60"
        >
          {searching ? "Шукаємо..." : "Шукати"}
        </button>
        <button
          type="button"
          onClick={() => setAdvanced(v => !v)}
          className="w-full rounded-full border border-ink bg-white py-3.5 text-[16px] font-semibold text-ink transition-colors hover:bg-surface"
        >
          {advanced ? "Сховати розширений пошук" : "Розширений пошук"}
        </button>
      </div>

      {advanced && (
        <div className="mt-4 space-y-4 rounded-2xl border border-border bg-white p-4">
          <div>
            <label className="mb-1.5 block text-[12px] font-semibold text-muted">Назва запиту</label>
            <input
              value={filters.name}
              onChange={e => update({ name: e.target.value })}
              placeholder="Camry під перепродаж"
              className="input-field"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-[12px] font-semibold text-muted">Пробіг, км</label>
            <div className="grid grid-cols-2 gap-2">
              <input
                value={filters.mileageFrom}
                onChange={e => update({ mileageFrom: formatPriceInput(e.target.value) })}
                placeholder="0"
                className="input-field"
                inputMode="numeric"
              />
              <input
                value={filters.mileageTo}
                onChange={e => update({ mileageTo: formatPriceInput(e.target.value) })}
                placeholder="200 000"
                className="input-field"
                inputMode="numeric"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-[12px] font-semibold text-muted">Джерела</label>
            <div className="flex flex-wrap gap-2">
              {SOURCE_OPTIONS.map(source => {
                const active = filters.sources.includes(source);
                return (
                  <button
                    key={source}
                    type="button"
                    onClick={() => update({ sources: toggleValue(filters.sources, source) })}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-[12px] font-medium transition-colors",
                      active
                        ? "border-emerald bg-emerald text-white"
                        : "border-border bg-white text-muted hover:border-emerald/40",
                    )}
                  >
                    {source}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            type="button"
            onClick={onReset}
            className="text-[12px] text-muted underline underline-offset-2 hover:text-ink"
          >
            Скинути всі фільтри
          </button>
        </div>
      )}
    </div>
  );
}
