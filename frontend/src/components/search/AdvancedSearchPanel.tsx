"use client";

import { FilterOptionsPopover } from "@/components/search/FilterOptionsPopover";
import { FilterRangePopover } from "@/components/search/FilterRangePopover";
import { cn } from "@/lib/utils";
import {
  COLOR_OPTIONS,
  DEFAULT_FILTERS,
  DRIVE_OPTIONS,
  FUEL_OPTIONS,
  SOURCE_OPTIONS,
  TRANSMISSION_OPTIONS,
  formatDecimalInput,
  formatPriceInput,
  toggleValue,
  type SearchFilterState,
} from "@/lib/search-catalog";

type Props = {
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
  onReset: () => void;
};

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="border-b border-border/60 pb-2 text-[15px] font-bold text-ink">{children}</h3>
  );
}

export function AdvancedSearchPanel({ filters, onChange, onReset }: Props) {
  const update = (patch: Partial<SearchFilterState>) => {
    onChange({ ...filters, ...patch });
  };

  return (
    <div className="mt-4 overflow-hidden rounded-[1.35rem] border border-border/80 bg-white shadow-[0_8px_30px_-12px_rgba(10,12,14,0.18)] ring-1 ring-black/[0.04]">
      <div className="border-b border-border/60 bg-surface/50 px-4 py-3.5 sm:px-5">
        <h2 className="text-[17px] font-bold text-ink">Розширений пошук авто</h2>
      </div>

      <div className="space-y-5 px-4 py-4 sm:px-5">
        <section className="space-y-2">
          <SectionTitle>Ціна</SectionTitle>
          <FilterRangePopover
            label="Ціна"
            from={filters.priceFrom}
            to={filters.priceTo}
            onChange={(priceFrom, priceTo) => update({ priceFrom, priceTo })}
            format={formatPriceInput}
            placeholderFrom="400 000"
            placeholderTo="900 000"
            suffix="грн"
          />
        </section>

        <section className="space-y-2">
          <SectionTitle>Технічні характеристики</SectionTitle>

          <FilterOptionsPopover
            label="Тип палива"
            value=""
            values={filters.fuels}
            options={[...FUEL_OPTIONS]}
            onChange={() => {}}
            onToggle={fuel => update({ fuels: toggleValue(filters.fuels, fuel) })}
            multiple
          />

          <FilterOptionsPopover
            label="Коробка передач"
            value=""
            values={filters.transmissions}
            options={[...TRANSMISSION_OPTIONS]}
            onChange={() => {}}
            onToggle={trans => update({ transmissions: toggleValue(filters.transmissions, trans) })}
            multiple
          />

          <FilterRangePopover
            label="Пробіг, тис. км"
            from={filters.mileageFrom}
            to={filters.mileageTo}
            onChange={(mileageFrom, mileageTo) => update({ mileageFrom, mileageTo })}
            format={v => v.replace(/[^\d]/g, "")}
            placeholderFrom="0"
            placeholderTo="200"
            suffix="тис. км"
          />

          <FilterRangePopover
            label="Об'єм двигуна, л"
            from={filters.engineVolumeFrom}
            to={filters.engineVolumeTo}
            onChange={(engineVolumeFrom, engineVolumeTo) => update({ engineVolumeFrom, engineVolumeTo })}
            format={v => formatDecimalInput(v, 1)}
            placeholderFrom="1.0"
            placeholderTo="3.5"
            suffix="л"
          />

          <FilterOptionsPopover
            label="Тип приводу"
            value=""
            values={filters.driveTypes}
            options={[...DRIVE_OPTIONS]}
            onChange={() => {}}
            onToggle={drive => update({ driveTypes: toggleValue(filters.driveTypes, drive) })}
            multiple
          />

          <FilterOptionsPopover
            label="Колір"
            value=""
            values={filters.colors}
            options={[...COLOR_OPTIONS]}
            onChange={() => {}}
            onToggle={color => update({ colors: toggleValue(filters.colors, color) })}
            multiple
          />

          <FilterRangePopover
            label="Витрата палива, л/100 км"
            from={filters.fuelConsumptionFrom}
            to={filters.fuelConsumptionTo}
            onChange={(fuelConsumptionFrom, fuelConsumptionTo) => update({ fuelConsumptionFrom, fuelConsumptionTo })}
            format={v => formatDecimalInput(v, 1)}
            placeholderFrom="5"
            placeholderTo="12"
            suffix="л/100 км"
          />

          <FilterRangePopover
            label="Запас ходу, км"
            from={filters.rangeFrom}
            to={filters.rangeTo}
            onChange={(rangeFrom, rangeTo) => update({ rangeFrom, rangeTo })}
            format={v => v.replace(/[^\d]/g, "")}
            placeholderFrom="300"
            placeholderTo="600"
            suffix="км"
          />

          <FilterRangePopover
            label="Ємність акумулятора, кВт·год"
            from={filters.batteryCapacityFrom}
            to={filters.batteryCapacityTo}
            onChange={(batteryCapacityFrom, batteryCapacityTo) => update({ batteryCapacityFrom, batteryCapacityTo })}
            format={v => formatDecimalInput(v, 1)}
            placeholderFrom="40"
            placeholderTo="100"
            suffix="кВт·год"
          />

          <FilterRangePopover
            label="Потужність"
            from={filters.powerFrom}
            to={filters.powerTo}
            onChange={(powerFrom, powerTo) => update({ powerFrom, powerTo })}
            format={v => v.replace(/[^\d]/g, "")}
            placeholderFrom="100"
            placeholderTo="300"
            suffix="к.с."
          />
        </section>

        <section className="space-y-3 border-t border-border/60 pt-4">
          <label className="block text-[12px] font-semibold text-muted">Назва запиту</label>
          <input
            value={filters.name}
            onChange={e => update({ name: e.target.value })}
            placeholder="Camry під перепродаж"
            className="input-field"
          />

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
        </section>
      </div>
    </div>
  );
}
