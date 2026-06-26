"use client";

import { IconFilter, IconLocation, IconPlay } from "@/components/icons";
import { FilterCombobox } from "@/components/search/FilterCombobox";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { BRANDS, getModelsForBrand, TOTAL_BRANDS, TOTAL_MODELS } from "@/lib/search-data/brands-models";
import { UKRAINE_REGIONS } from "@/lib/search-data/regions";
import {
  DEFAULT_FILTERS,
  FUEL_OPTIONS,
  SOURCE_OPTIONS,
  TRANSMISSION_OPTIONS,
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.08em] text-muted">{label}</label>
      {children}
    </div>
  );
}

export function SearchFiltersPanel({ filters, onChange, onReset, onSearch, searching }: Props) {
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

  return (
    <aside className="sticky top-[80px] w-[300px] shrink-0">
      <div className="flex max-h-[calc(100vh-96px)] flex-col rounded-xl border border-border bg-white">
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-4">
          <span className="flex items-center gap-2 text-[13px] font-semibold text-ink">
            <IconFilter size={13} className="text-muted" />
            Фільтри
          </span>
          <button
            type="button"
            onClick={onReset}
            className="text-[11px] text-muted underline underline-offset-2 hover:text-ink"
          >
            Скинути
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <Field label="Назва запиту">
            <input
              value={filters.name}
              onChange={e => update({ name: e.target.value })}
              placeholder="Camry під перепродаж"
              className="input-field"
            />
          </Field>

          <Field label={`Регіон · ${UKRAINE_REGIONS.length - 1} областей`}>
            <div className="flex items-center gap-2">
              <IconLocation size={13} className="shrink-0 text-muted" />
              <FilterCombobox
                value={filters.region}
                onChange={region => update({ region: region || "Вся Україна" })}
                options={[...UKRAINE_REGIONS]}
                placeholder="Оберіть регіон"
                emptyLabel="Вся Україна"
                className="flex-1"
              />
            </div>
          </Field>

          <Field label={`Марка · ${TOTAL_BRANDS} марок`}>
            <FilterCombobox
              value={filters.brand}
              onChange={handleBrandChange}
              options={BRANDS}
              placeholder="Toyota, BMW, Volkswagen..."
              emptyLabel="Будь-яка марка"
            />
          </Field>

          <Field label={filters.brand ? `Модель · ${models.length} моделей` : "Модель"}>
            <FilterCombobox
              value={filters.model}
              onChange={model => update({ model })}
              options={models}
              placeholder={filters.brand ? "Camry, Passat..." : "Спочатку оберіть марку"}
              emptyLabel="Будь-яка модель"
              disabled={!filters.brand}
            />
          </Field>

          <Field label="Рік">
            <div className="flex items-center gap-2">
              <input
                value={filters.yearFrom}
                onChange={e => update({ yearFrom: e.target.value.replace(/[^\d]/g, "").slice(0, 4) })}
                placeholder={DEFAULT_FILTERS.yearFrom}
                className="input-field w-full"
                inputMode="numeric"
              />
              <span className="text-[12px] text-muted">—</span>
              <input
                value={filters.yearTo}
                onChange={e => update({ yearTo: e.target.value.replace(/[^\d]/g, "").slice(0, 4) })}
                placeholder={DEFAULT_FILTERS.yearTo}
                className="input-field w-full"
                inputMode="numeric"
              />
            </div>
          </Field>

          <Field label="Ціна, грн">
            <div className="flex items-center gap-2">
              <input
                value={filters.priceFrom}
                onChange={e => update({ priceFrom: formatPriceInput(e.target.value) })}
                placeholder="400 000"
                className="input-field w-full"
                inputMode="numeric"
              />
              <span className="text-[12px] text-muted">—</span>
              <input
                value={filters.priceTo}
                onChange={e => update({ priceTo: formatPriceInput(e.target.value) })}
                placeholder="900 000"
                className="input-field w-full"
                inputMode="numeric"
              />
            </div>
          </Field>

          <Field label="Пробіг, км">
            <div className="flex items-center gap-2">
              <input
                value={filters.mileageFrom}
                onChange={e => update({ mileageFrom: formatPriceInput(e.target.value) })}
                placeholder="0"
                className="input-field w-full"
                inputMode="numeric"
              />
              <span className="text-[12px] text-muted">—</span>
              <input
                value={filters.mileageTo}
                onChange={e => update({ mileageTo: formatPriceInput(e.target.value) })}
                placeholder="200 000"
                className="input-field w-full"
                inputMode="numeric"
              />
            </div>
          </Field>

          <Field label="Двигун">
            <div className="flex flex-wrap gap-1.5">
              {FUEL_OPTIONS.map(value => (
                <button
                  key={value}
                  type="button"
                  onClick={() => update({ fuels: toggleValue(filters.fuels, value) })}
                  className={cn(
                    "rounded border px-2.5 py-1 text-[11px] font-medium transition-colors",
                    filters.fuels.includes(value)
                      ? "border-ink bg-ink text-white"
                      : "border-border bg-white text-muted hover:border-ink/20",
                  )}
                >
                  {value}
                </button>
              ))}
            </div>
          </Field>

          <Field label="КПП">
            <div className="flex flex-wrap gap-1.5">
              {TRANSMISSION_OPTIONS.map(value => (
                <button
                  key={value}
                  type="button"
                  onClick={() => update({ transmissions: toggleValue(filters.transmissions, value) })}
                  className={cn(
                    "rounded border px-2.5 py-1 text-[11px] font-medium transition-colors",
                    filters.transmissions.includes(value)
                      ? "border-ink bg-ink text-white"
                      : "border-border bg-white text-muted hover:border-ink/20",
                  )}
                >
                  {value}
                </button>
              ))}
            </div>
          </Field>

          <Field label="Джерела">
            <div className="space-y-2">
              {SOURCE_OPTIONS.map(value => (
                <label key={value} className="flex cursor-pointer items-center gap-2">
                  <span
                    onClick={() => update({ sources: toggleValue(filters.sources, value) })}
                    className={cn(
                      "flex h-4 w-4 items-center justify-center rounded border transition-colors",
                      filters.sources.includes(value) ? "border-ink bg-ink" : "border-border bg-white",
                    )}
                  >
                    {filters.sources.includes(value) && (
                      <svg width="8" height="8" viewBox="0 0 10 10" fill="none">
                        <path d="M2 5l2.5 2.5L8 2" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </span>
                  <span className="text-[13px] text-ink">{value}</span>
                </label>
              ))}
            </div>
          </Field>

          <p className="text-[10px] leading-relaxed text-muted">
            Каталог: {TOTAL_BRANDS} марок · {TOTAL_MODELS} моделей · {UKRAINE_REGIONS.length - 1} регіонів
          </p>
        </div>

        <div className="space-y-2 border-t border-border/60 px-5 py-4">
          <Button
            onClick={onSearch}
            variant="primary"
            size="md"
            className="w-full gap-1.5"
            loading={searching}
          >
            <IconPlay size={13} />
            Запустити пошук
          </Button>
          <Button variant="secondary" size="md" className="w-full text-[12px]" disabled>
            Зберегти шаблон
          </Button>
        </div>
      </div>
    </aside>
  );
}
