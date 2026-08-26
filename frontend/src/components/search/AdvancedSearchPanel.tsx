"use client";

import Image from "next/image";
import { ColorSwatchPicker } from "@/components/search/ColorSwatchPicker";
import { FilterAccordionSection } from "@/components/search/FilterAccordionSection";
import { FilterChipGroup } from "@/components/search/FilterChipGroup";
import { FilterInlineRange } from "@/components/search/FilterInlineRange";
import { FilterPublishedDateRange } from "@/components/search/FilterPublishedDateRange";
import {
  FilterBooleanRow,
  FilterSegmentedRow,
  FilterTriStateRow,
} from "@/components/search/FilterTriStateRow";
import { cn } from "@/lib/utils";
import {
  ACCIDENT_FILTER_OPTIONS,
  BODY_TYPE_OPTIONS,
  COLOR_HEX_BY_NAME,
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
import { sourceFilterIcon } from "@/lib/listing-source";
import { formatPublishedFilterSummary } from "@/lib/published-date-filter";
import type { SearchFreshness } from "@/lib/search-preview";

type Props = {
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
  onReset: () => void;
  freshness?: SearchFreshness;
  onFreshnessChange?: (freshness: SearchFreshness) => void;
};

function ActiveSummary({
  filters,
  freshness = "all",
  onClearOne,
  onFreshnessChange,
}: {
  filters: SearchFilterState;
  freshness?: SearchFreshness;
  onClearOne: (patch: Partial<SearchFilterState>) => void;
  onFreshnessChange?: (freshness: SearchFreshness) => void;
}) {
  const chips: { key: string; label: string; clear: () => void; swatch?: string }[] = [];

  for (const body of filters.bodyTypes) {
    chips.push({
      key: `body-${body}`,
      label: body,
      clear: () => onClearOne({ bodyTypes: filters.bodyTypes.filter(v => v !== body) }),
    });
  }
  for (const fuel of filters.fuels) {
    chips.push({
      key: `fuel-${fuel}`,
      label: fuel,
      clear: () => onClearOne({ fuels: filters.fuels.filter(v => v !== fuel) }),
    });
  }
  for (const gear of filters.transmissions) {
    chips.push({
      key: `gear-${gear}`,
      label: gear,
      clear: () => onClearOne({ transmissions: filters.transmissions.filter(v => v !== gear) }),
    });
  }
  for (const drive of filters.driveTypes) {
    chips.push({
      key: `drive-${drive}`,
      label: drive,
      clear: () => onClearOne({ driveTypes: filters.driveTypes.filter(v => v !== drive) }),
    });
  }
  for (const color of filters.colors) {
    chips.push({
      key: `color-${color}`,
      label: color,
      swatch: COLOR_HEX_BY_NAME[color],
      clear: () => onClearOne({ colors: filters.colors.filter(v => v !== color) }),
    });
  }
  if (filters.metallic) {
    chips.push({ key: "metallic", label: "Металік", clear: () => onClearOne({ metallic: false }) });
  }
  if (filters.zeroMileage) {
    chips.push({
      key: "zero",
      label: "Без пробігу",
      clear: () => onClearOne({ zeroMileage: false }),
    });
  }
  if (filters.mileageFrom || filters.mileageTo) {
    chips.push({
      key: "mileage",
      label: `Пробіг ${filters.mileageFrom || "…"}–${filters.mileageTo || "…"}`,
      clear: () => onClearOne({ mileageFrom: "", mileageTo: "" }),
    });
  }
  if (filters.engineVolumeFrom || filters.engineVolumeTo) {
    chips.push({
      key: "engine",
      label: `Обʼєм ${filters.engineVolumeFrom || "…"}–${filters.engineVolumeTo || "…"} л`,
      clear: () => onClearOne({ engineVolumeFrom: "", engineVolumeTo: "" }),
    });
  }
  if (filters.powerFrom || filters.powerTo) {
    chips.push({
      key: "power",
      label: `${filters.powerFrom || "…"}–${filters.powerTo || "…"} ${filters.powerUnit === "kw" ? "кВт" : "к.с."}`,
      clear: () => onClearOne({ powerFrom: "", powerTo: "" }),
    });
  }
  if (filters.seatsFrom || filters.seatsTo) {
    chips.push({
      key: "seats",
      label: `${filters.seatsFrom || "…"}–${filters.seatsTo || "…"} міс.`,
      clear: () => onClearOne({ seatsFrom: "", seatsTo: "" }),
    });
  }
  if (filters.doorsFrom || filters.doorsTo) {
    chips.push({
      key: "doors",
      label: `${filters.doorsFrom || "…"}–${filters.doorsTo || "…"} двер.`,
      clear: () => onClearOne({ doorsFrom: "", doorsTo: "" }),
    });
  }
  if (filters.accident) {
    const label = ACCIDENT_FILTER_OPTIONS.find(o => o.value === filters.accident)?.label || filters.accident;
    chips.push({
      key: "accident",
      label: `ДТП: ${label}`,
      clear: () => onClearOne({ accident: "" }),
    });
  }
  if (filters.sellerFilter) {
    const label =
      SELLER_FILTER_OPTIONS.find(o => o.value === filters.sellerFilter)?.label || filters.sellerFilter;
    chips.push({
      key: "seller",
      label,
      clear: () => onClearOne({ sellerFilter: "" }),
    });
  }
  if (filters.vinVerified) {
    chips.push({
      key: "vin",
      label: "VIN перевірений",
      clear: () => onClearOne({ vinVerified: false }),
    });
  }
  if (filters.bargain) {
    chips.push({ key: "bargain", label: "Торг", clear: () => onClearOne({ bargain: false }) });
  }
  if (filters.inCredit) {
    chips.push({
      key: "credit",
      label: filters.inCredit === "show" ? "В кредиті" : "Без кредиту",
      clear: () => onClearOne({ inCredit: "" }),
    });
  }
  if (filters.usaImport) {
    chips.push({
      key: "usa",
      label: filters.usaImport === "show" ? "З США" : "Не з США",
      clear: () => onClearOne({ usaImport: "" }),
    });
  }
  if (filters.notCustoms) {
    chips.push({
      key: "customs",
      label: filters.notCustoms === "show" ? "Нерозмитнені" : "Розмитнені",
      clear: () => onClearOne({ notCustoms: "" }),
    });
  }
  const publishedSummary = formatPublishedFilterSummary(
    filters.publishedOlderThanDays,
    filters.publishedFrom,
    filters.publishedTo,
    freshness,
  );
  if (publishedSummary) {
    chips.push({
      key: "published",
      label: `Вік: ${publishedSummary}`,
      clear: () => {
        onFreshnessChange?.("all");
        onClearOne({ publishedOlderThanDays: "", publishedFrom: "", publishedTo: "" });
      },
    });
  }

  if (chips.length === 0) return null;

  return (
    <div className="rounded-xl border border-emerald/20 bg-emerald/[0.04] px-3 py-2.5">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-emerald-dark/80">
        Активні фільтри · {chips.length}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {chips.map(chip => (
          <button
            key={chip.key}
            type="button"
            onClick={chip.clear}
            className="inline-flex items-center gap-1.5 rounded-full border border-emerald/25 bg-white px-2.5 py-1 text-[11px] font-medium text-ink transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-700"
            title="Прибрати"
          >
            {chip.swatch ? (
              <span
                className="h-3 w-3 rounded-full border border-black/10"
                style={{ backgroundColor: chip.swatch }}
                aria-hidden
              />
            ) : null}
            {chip.label}
            <span className="text-muted">×</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function AdvancedSearchPanel({
  filters,
  onChange,
  onReset,
  freshness = "all",
  onFreshnessChange,
}: Props) {
  const update = (patch: Partial<SearchFilterState>) => {
    onChange({ ...filters, ...patch });
  };

  const resetAdvanced = () => {
    onChange(resetAdvancedFilters(filters));
    onFreshnessChange?.("all");
  };

  const techBadge = countAdvancedFilterFields(filters, "technical");
  const publishedBadge =
    countAdvancedFilterFields(filters, "published") + (freshness === "new" ? 1 : 0);
  const conditionBadge = countAdvancedFilterFields(filters, "condition");
  const originBadge = countAdvancedFilterFields(filters, "origin");
  const sourcesBadge =
    filters.sources.length === SOURCE_OPTIONS.length ? 0 : filters.sources.length;
  const totalActive = techBadge + publishedBadge + conditionBadge + originBadge + (sourcesBadge > 0 ? 1 : 0);

  return (
    <div className="mt-4 overflow-hidden rounded-[1.35rem] border border-border/80 bg-white shadow-[0_8px_30px_-12px_rgba(10,12,14,0.18)] ring-1 ring-black/[0.04]">
      <div className="flex items-center justify-between gap-3 border-b border-border/60 bg-surface/50 px-4 py-3.5 sm:px-5">
        <h2 className="text-[17px] font-bold text-ink">Розширений пошук</h2>
        {totalActive > 0 ? (
          <button
            type="button"
            onClick={resetAdvanced}
            className="shrink-0 rounded-full border border-border px-3 py-1.5 text-[12px] font-medium text-muted transition-colors hover:border-emerald/40 hover:text-ink"
          >
            Скинути ({totalActive})
          </button>
        ) : null}
      </div>

      <div className="relative z-20 space-y-4 overflow-visible px-4 py-4 sm:px-5">
        <ActiveSummary
          filters={filters}
          freshness={freshness}
          onClearOne={update}
          onFreshnessChange={onFreshnessChange}
        />

        <FilterAccordionSection title="Вік оголошення" badge={publishedBadge} defaultOpen={false}>
          {onFreshnessChange ? (
            <FilterPublishedDateRange
              freshness={freshness}
              publishedOlderThanDays={filters.publishedOlderThanDays}
              publishedFrom={filters.publishedFrom}
              publishedTo={filters.publishedTo}
              onFreshnessChange={onFreshnessChange}
              onChange={update}
            />
          ) : null}
        </FilterAccordionSection>

        <FilterAccordionSection title="Кузов і техніка" badge={techBadge} defaultOpen={false}>
          <FilterChipGroup
            label="Тип кузова"
            options={BODY_TYPE_OPTIONS}
            values={filters.bodyTypes}
            onToggle={body => update({ bodyTypes: toggleValue(filters.bodyTypes, body) })}
          />

          <FilterChipGroup
            label="Тип палива"
            options={FUEL_OPTIONS}
            values={filters.fuels}
            onToggle={fuel => update({ fuels: toggleValue(filters.fuels, fuel) })}
          />

          <FilterChipGroup
            label="Коробка передач"
            options={TRANSMISSION_OPTIONS}
            values={filters.transmissions}
            onToggle={trans => update({ transmissions: toggleValue(filters.transmissions, trans) })}
          />

          <FilterChipGroup
            label="Привід"
            options={DRIVE_OPTIONS}
            values={filters.driveTypes}
            onToggle={drive => update({ driveTypes: toggleValue(filters.driveTypes, drive) })}
          />

          <div className="grid grid-cols-1 gap-3 border-t border-border/60 pt-4 sm:grid-cols-2">
            <FilterInlineRange
              label="Пробіг"
              suffix="тис. км"
              from={filters.mileageFrom}
              to={filters.mileageTo}
              onChange={(mileageFrom, mileageTo) => update({ mileageFrom, mileageTo })}
              format={v => v.replace(/[^\d]/g, "")}
              placeholderFrom="0"
              placeholderTo="200"
              trailing={
                <button
                  type="button"
                  onClick={() =>
                    update({
                      zeroMileage: !filters.zeroMileage,
                      ...(filters.zeroMileage ? {} : { mileageFrom: "0", mileageTo: "0" }),
                    })
                  }
                  className={cn(
                    "rounded-full border px-2 py-0.5 text-[10px] font-semibold transition-colors",
                    filters.zeroMileage
                      ? "border-emerald bg-emerald text-white"
                      : "border-border text-muted hover:border-emerald/40",
                  )}
                >
                  0 км
                </button>
              }
            />
            <FilterInlineRange
              label="Обʼєм двигуна"
              suffix="л"
              from={filters.engineVolumeFrom}
              to={filters.engineVolumeTo}
              onChange={(engineVolumeFrom, engineVolumeTo) =>
                update({ engineVolumeFrom, engineVolumeTo })
              }
              format={v => formatDecimalInput(v, 1)}
              placeholderFrom="1.0"
              placeholderTo="3.5"
              inputMode="decimal"
            />
          </div>

          <div className="grid gap-3 border-t border-border/60 pt-4 sm:grid-cols-1">
            <FilterInlineRange
              label="Потужність"
              suffix={filters.powerUnit === "kw" ? "кВт" : "к.с."}
              from={filters.powerFrom}
              to={filters.powerTo}
              onChange={(powerFrom, powerTo) => update({ powerFrom, powerTo })}
              format={v => v.replace(/[^\d]/g, "")}
              placeholderFrom="100"
              placeholderTo="300"
              trailing={
                <div className="flex rounded-full border border-border bg-surface p-0.5">
                  {(["hp", "kw"] as const).map(unit => (
                    <button
                      key={unit}
                      type="button"
                      onClick={() => update({ powerUnit: unit })}
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-semibold transition-colors",
                        filters.powerUnit === unit
                          ? "bg-white text-ink shadow-sm"
                          : "text-muted hover:text-ink",
                      )}
                    >
                      {unit === "hp" ? "к.с." : "кВт"}
                    </button>
                  ))}
                </div>
              }
            />
            <div className="grid grid-cols-2 gap-3">
              <FilterInlineRange
                label="Місця"
                from={filters.seatsFrom}
                to={filters.seatsTo}
                onChange={(seatsFrom, seatsTo) => update({ seatsFrom, seatsTo })}
                format={v => v.replace(/[^\d]/g, "")}
                placeholderFrom="5"
                placeholderTo="7"
              />
              <FilterInlineRange
                label="Двері"
                from={filters.doorsFrom}
                to={filters.doorsTo}
                onChange={(doorsFrom, doorsTo) => update({ doorsFrom, doorsTo })}
                format={v => v.replace(/[^\d]/g, "")}
                placeholderFrom="3"
                placeholderTo="5"
              />
            </div>
          </div>

          <ColorSwatchPicker
            values={filters.colors}
            onToggle={color => update({ colors: toggleValue(filters.colors, color) })}
            metallic={filters.metallic}
            onMetallicChange={metallic => update({ metallic })}
          />

          <details className="group rounded-xl border border-border/60 bg-surface/30 open:bg-white">
            <summary className="cursor-pointer list-none px-3 py-2.5 text-[12px] font-semibold text-muted marker:content-none [&::-webkit-details-marker]:hidden">
              <span className="flex items-center justify-between gap-2">
                Електро / витрата
                <span className="text-[11px] font-normal text-muted/70 group-open:hidden">опційно</span>
              </span>
            </summary>
            <div className="space-y-3 border-t border-border/50 px-3 py-3">
              <FilterInlineRange
                label="Витрата палива"
                suffix="л/100 км"
                from={filters.fuelConsumptionFrom}
                to={filters.fuelConsumptionTo}
                onChange={(fuelConsumptionFrom, fuelConsumptionTo) =>
                  update({ fuelConsumptionFrom, fuelConsumptionTo })
                }
                format={v => formatDecimalInput(v, 1)}
                placeholderFrom="5"
                placeholderTo="12"
                inputMode="decimal"
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <FilterInlineRange
                  label="Запас ходу"
                  suffix="км"
                  from={filters.rangeFrom}
                  to={filters.rangeTo}
                  onChange={(rangeFrom, rangeTo) => update({ rangeFrom, rangeTo })}
                  format={v => v.replace(/[^\d]/g, "")}
                  placeholderFrom="300"
                  placeholderTo="600"
                />
                <FilterInlineRange
                  label="Батарея"
                  suffix="кВт·год"
                  from={filters.batteryCapacityFrom}
                  to={filters.batteryCapacityTo}
                  onChange={(batteryCapacityFrom, batteryCapacityTo) =>
                    update({ batteryCapacityFrom, batteryCapacityTo })
                  }
                  format={v => formatDecimalInput(v, 1)}
                  placeholderFrom="40"
                  placeholderTo="100"
                  inputMode="decimal"
                />
              </div>
            </div>
          </details>
        </FilterAccordionSection>

        <FilterAccordionSection title="Стан та історія" badge={conditionBadge} defaultOpen={false}>
          <div className="space-y-3 rounded-xl border border-border/60 bg-surface/20 p-3">
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
              label="Власників, макс."
              value={filters.ownersMax}
              options={OWNERS_FILTER_OPTIONS}
              onChange={ownersMax => update({ ownersMax })}
            />
            <FilterTriStateRow
              label="В кредиті"
              value={filters.inCredit}
              onChange={inCredit => update({ inCredit })}
            />
            <div className="grid gap-2 sm:grid-cols-2">
              <FilterBooleanRow
                label="Перевірений VIN"
                checked={filters.vinVerified}
                onChange={vinVerified => update({ vinVerified })}
              />
              <FilterBooleanRow
                label="Торг"
                checked={filters.bargain}
                onChange={bargain => update({ bargain })}
              />
            </div>
          </div>
        </FilterAccordionSection>

        <FilterAccordionSection title="Походження" badge={originBadge} defaultOpen={false}>
          <div className="space-y-3 rounded-xl border border-border/60 bg-surface/20 p-3">
            <FilterTriStateRow
              label="Авто з США"
              value={filters.usaImport}
              onChange={usaImport => update({ usaImport })}
            />
            <FilterTriStateRow
              label="Нерозмитнені"
              value={filters.notCustoms}
              onChange={notCustoms => update({ notCustoms })}
            />
          </div>
        </FilterAccordionSection>

        <FilterAccordionSection title="Джерела" badge={sourcesBadge} defaultOpen={false}>
          <div className="flex flex-wrap gap-2">
            {SOURCE_OPTIONS.map(source => {
              const active = filters.sources.includes(source);
              const icon = sourceFilterIcon(source);
              return (
                <button
                  key={source}
                  type="button"
                  onClick={() => update({ sources: toggleValue(filters.sources, source) })}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-[12px] font-medium transition-colors sm:px-3",
                    active
                      ? "border-emerald bg-emerald text-white"
                      : "border-border bg-white text-muted hover:border-emerald/40",
                  )}
                >
                  {icon ? (
                    <span
                      className={cn(
                        "relative inline-flex h-5 w-5 shrink-0 overflow-hidden rounded-full bg-white ring-1",
                        active ? "ring-white/30" : "ring-black/5",
                      )}
                    >
                      <Image
                        src={icon}
                        alt=""
                        width={20}
                        height={20}
                        className="h-full w-full object-cover"
                        unoptimized
                      />
                    </span>
                  ) : null}
                  {source}
                </button>
              );
            })}
          </div>
        </FilterAccordionSection>

        <section className="border-t border-border/60 pt-4">
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            <button
              type="button"
              onClick={resetAdvanced}
              className="text-[12px] text-muted underline underline-offset-2 hover:text-ink"
            >
              Скинути розширені
            </button>
            <button
              type="button"
              onClick={onReset}
              className="text-[12px] text-muted underline underline-offset-2 hover:text-ink"
            >
              Скинути всі
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
