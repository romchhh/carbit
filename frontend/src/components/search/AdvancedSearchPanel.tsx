"use client";

import { FilterAccordionSection } from "@/components/search/FilterAccordionSection";
import { FilterOptionsPopover } from "@/components/search/FilterOptionsPopover";
import { FilterRangePopover } from "@/components/search/FilterRangePopover";
import {
  FilterBooleanRow,
  FilterSegmentedRow,
  FilterTriStateRow,
} from "@/components/search/FilterTriStateRow";
import { cn } from "@/lib/utils";
import {
  ACCIDENT_FILTER_OPTIONS,
  BODY_TYPE_OPTIONS,
  COLOR_OPTIONS,
  DRIVE_OPTIONS,
  FUEL_OPTIONS,
  OWNERS_FILTER_OPTIONS,
  SELLER_FILTER_OPTIONS,
  SOURCE_OPTIONS,
  TRANSMISSION_OPTIONS,
  countAdvancedFilterFields,
  formatDecimalInput,
  toggleValue,
  type SearchFilterState,
} from "@/lib/search-catalog";
import { resetAdvancedFilters } from "@/lib/search-filters-api";

type Props = {
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
  onReset: () => void;
};

export function AdvancedSearchPanel({ filters, onChange, onReset }: Props) {
  const update = (patch: Partial<SearchFilterState>) => {
    onChange({ ...filters, ...patch });
  };

  const techBadge = countAdvancedFilterFields(filters, "technical");
  const conditionBadge = countAdvancedFilterFields(filters, "condition");
  const originBadge = countAdvancedFilterFields(filters, "origin");

  return (
    <div className="mt-4 rounded-[1.35rem] border border-border/80 bg-white shadow-[0_8px_30px_-12px_rgba(10,12,14,0.18)] ring-1 ring-black/[0.04]">
      <div className="overflow-hidden rounded-t-[1.35rem] border-b border-border/60 bg-surface/50 px-4 py-3.5 sm:px-5">
        <h2 className="text-[17px] font-bold text-ink">Розширений пошук</h2>
        <p className="mt-0.5 text-[12px] text-muted">
          Як на AUTO.RIA — техніка, стан, походження. AUTO.RIA отримує максимум параметрів у запиті.
        </p>
      </div>

      <div className="relative z-20 space-y-1 overflow-visible px-4 py-4 sm:px-5">
        <FilterAccordionSection title="Технічні характеристики" badge={techBadge} defaultOpen>
          <FilterOptionsPopover
            label="Тип кузова"
            value=""
            values={filters.bodyTypes}
            options={[...BODY_TYPE_OPTIONS]}
            onChange={() => {}}
            onToggle={body => update({ bodyTypes: toggleValue(filters.bodyTypes, body) })}
            multiple
          />

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

          <FilterBooleanRow
            label="Без пробігу"
            checked={filters.zeroMileage}
            onChange={zeroMileage => update({ zeroMileage })}
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

          <FilterBooleanRow
            label="Металік"
            checked={filters.metallic}
            onChange={metallic => update({ metallic })}
          />

          <FilterRangePopover
            label="Витрата палива, л/100 км"
            from={filters.fuelConsumptionFrom}
            to={filters.fuelConsumptionTo}
            onChange={(fuelConsumptionFrom, fuelConsumptionTo) =>
              update({ fuelConsumptionFrom, fuelConsumptionTo })
            }
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
            onChange={(batteryCapacityFrom, batteryCapacityTo) =>
              update({ batteryCapacityFrom, batteryCapacityTo })
            }
            format={v => formatDecimalInput(v, 1)}
            placeholderFrom="40"
            placeholderTo="100"
            suffix="кВт·год"
          />

          <div className="space-y-2">
            <FilterSegmentedRow
              label="Одиниця потужності"
              value={filters.powerUnit}
              options={[
                { value: "hp", label: "к.с." },
                { value: "kw", label: "кВт" },
              ]}
              onChange={powerUnit => update({ powerUnit })}
            />
            <FilterRangePopover
              label="Потужність"
              from={filters.powerFrom}
              to={filters.powerTo}
              onChange={(powerFrom, powerTo) => update({ powerFrom, powerTo })}
              format={v => v.replace(/[^\d]/g, "")}
              placeholderFrom="100"
              placeholderTo="300"
              suffix={filters.powerUnit === "kw" ? "кВт" : "к.с."}
            />
          </div>

          <FilterRangePopover
            label="Кількість місць"
            from={filters.seatsFrom}
            to={filters.seatsTo}
            onChange={(seatsFrom, seatsTo) => update({ seatsFrom, seatsTo })}
            format={v => v.replace(/[^\d]/g, "")}
            placeholderFrom="5"
            placeholderTo="7"
            suffix="міс."
          />

          <FilterRangePopover
            label="Кількість дверей"
            from={filters.doorsFrom}
            to={filters.doorsTo}
            onChange={(doorsFrom, doorsTo) => update({ doorsFrom, doorsTo })}
            format={v => v.replace(/[^\d]/g, "")}
            placeholderFrom="3"
            placeholderTo="5"
            suffix="двер."
          />
        </FilterAccordionSection>

        <FilterAccordionSection title="Стан та історія" badge={conditionBadge} defaultOpen={false}>
          <FilterSegmentedRow
            label="Участь у ДТП"
            value={filters.accident}
            options={ACCIDENT_FILTER_OPTIONS}
            onChange={accident => update({ accident })}
          />

          <FilterSegmentedRow
            label="Продавець"
            value={filters.sellerFilter}
            options={SELLER_FILTER_OPTIONS}
            onChange={sellerFilter => update({ sellerFilter })}
          />

          <FilterSegmentedRow
            label="Власників в Україні, макс."
            value={filters.ownersMax}
            options={OWNERS_FILTER_OPTIONS}
            onChange={ownersMax => update({ ownersMax })}
          />

          <FilterBooleanRow
            label="Перевірений VIN"
            checked={filters.vinVerified}
            onChange={vinVerified => update({ vinVerified })}
          />

          <FilterBooleanRow label="Торг" checked={filters.bargain} onChange={bargain => update({ bargain })} />

          <FilterTriStateRow
            label="В кредиті"
            value={filters.inCredit}
            onChange={inCredit => update({ inCredit })}
          />
        </FilterAccordionSection>

        <FilterAccordionSection title="Походження та наявність" badge={originBadge} defaultOpen={false}>
          <FilterTriStateRow
            label="Авто з США"
            value={filters.usaImport}
            onChange={usaImport => update({ usaImport })}
          />

          <FilterTriStateRow
            label="Нерозмитнені (під пригон)"
            value={filters.notCustoms}
            onChange={notCustoms => update({ notCustoms })}
          />
        </FilterAccordionSection>

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
            onClick={() => onChange(resetAdvancedFilters(filters))}
            className="text-[12px] text-muted underline underline-offset-2 hover:text-ink"
          >
            Скинути розширені фільтри
          </button>
          <button
            type="button"
            onClick={onReset}
            className="ml-4 text-[12px] text-muted underline underline-offset-2 hover:text-ink"
          >
            Скинути всі фільтри
          </button>
        </section>
      </div>
    </div>
  );
}
