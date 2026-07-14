"use client";

import { ExportMenu } from "@/components/search/ExportMenu";
import type { ExportListing } from "@/lib/export-listings";
import type { SortOption } from "@/lib/search-catalog";

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "newest", label: "Спочатку нові" },
  { value: "price_asc", label: "Спочатку дешеві" },
  { value: "price_desc", label: "Спочатку дорогі" },
  { value: "year_desc", label: "За роком випуску" },
  { value: "mileage_asc", label: "За пробігом" },
];

type Props = {
  running: boolean;
  total: number;
  shown: number;
  sort: SortOption;
  onSortChange: (sort: SortOption) => void;
  exportItems: ExportListing[];
  exportName: string;
  isActive?: boolean;
  newCount?: number;
  idleLabel?: string;
};

export function SearchResultsToolbar({
  running,
  total,
  shown,
  sort,
  onSortChange,
  exportItems,
  exportName,
  isActive,
  newCount,
  idleLabel = "Натисніть «Шукати»",
}: Props) {
  return (
    <div className="mb-4 rounded-2xl border border-border bg-white p-3.5 sm:px-5 sm:py-3.5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 text-[13px]">
          {running ? (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              {isActive !== undefined ? (
                <>
                  <span
                    className={
                      isActive
                        ? "flex items-center gap-2 font-medium text-emerald-dark"
                        : "font-medium text-muted"
                    }
                  >
                    {isActive && (
                      <span className="h-2 w-2 animate-pulse rounded-full bg-emerald" />
                    )}
                    {isActive ? "Активний" : "Неактивний"}
                  </span>
                  <span className="text-border">·</span>
                </>
              ) : (
                <>
                  <span className="flex items-center gap-2 font-medium text-emerald-dark">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-emerald" />
                    Улов з ринку
                  </span>
                  <span className="text-border">·</span>
                </>
              )}
              <span className="text-muted">
                Знайдено <strong className="text-ink">{total.toLocaleString("uk-UA")}</strong>
                {shown < total && (
                  <span className="hidden sm:inline"> · показано {shown}</span>
                )}
              </span>
              {typeof newCount === "number" && newCount > 0 && (
                <>
                  <span className="text-border">·</span>
                  <span className="font-semibold text-emerald-dark">{newCount} нових</span>
                </>
              )}
              {shown < total && (
                <span className="w-full text-[12px] text-muted sm:hidden">
                  Показано {shown} з {total.toLocaleString("uk-UA")}
                </span>
              )}
            </div>
          ) : (
            <span className="text-muted">{idleLabel}</span>
          )}
        </div>

        {running && (
          <div className="flex items-center gap-2 sm:gap-3">
            <ExportMenu items={exportItems} filename={exportName} />
            <select
              value={sort}
              onChange={e => onSortChange(e.target.value as SortOption)}
              className="min-w-0 flex-1 rounded-xl border border-border bg-surface px-3 py-2.5 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-emerald/20 sm:flex-none sm:rounded-lg sm:bg-white sm:py-1.5 sm:text-[12px] sm:text-muted"
            >
              {SORT_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
}
