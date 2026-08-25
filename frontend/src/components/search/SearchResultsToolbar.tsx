"use client";

import { ExportMenu } from "@/components/search/ExportMenu";
import type { ExportListing } from "@/lib/export-listings";
import type { SortOption } from "@/lib/search-catalog";
import { ukPlural } from "@/lib/utils";

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "newest", label: "Спочатку нові" },
  { value: "published_asc", label: "Спочатку старі" },
  { value: "price_drop_desc", label: "За зниженням ціни" },
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
  priceDropCount?: number;
  idleLabel?: string;
  /** Сирі пропозиції до склеювання дублів. */
  offerCount?: number;
  duplicateCount?: number;
  hasMore?: boolean;
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
  priceDropCount,
  idleLabel = "Натисніть «Шукати»",
  offerCount,
  duplicateCount,
  hasMore = false,
}: Props) {
  return (
    <div className="mb-4 rounded-2xl border border-border bg-white p-3.5 sm:px-5 sm:py-3.5 lg:mb-5 lg:px-6 lg:py-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 text-[13px] lg:text-[14px]">
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
                <FoundCount
                  cards={total}
                  shown={shown}
                  offers={offerCount}
                  duplicates={duplicateCount}
                  hasMore={hasMore}
                />
              </span>
              {typeof newCount === "number" && newCount > 0 && (
                <>
                  <span className="text-border">·</span>
                  <span className="font-semibold text-emerald-dark">{newCount} нових</span>
                </>
              )}
              {typeof priceDropCount === "number" && priceDropCount > 0 && (
                <>
                  <span className="text-border">·</span>
                  <span className="font-semibold text-rose-700">{priceDropCount} зі зниженням</span>
                </>
              )}
              {hasMore && shown < total && (
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
              className="min-w-0 flex-1 rounded-xl border border-border bg-surface px-3 py-2.5 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-emerald/20 sm:flex-none sm:rounded-lg sm:bg-white sm:py-1.5 sm:text-[12px] sm:text-muted lg:px-3.5 lg:py-2 lg:text-[13px]"
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

function FoundCount({
  cards,
  shown,
  offers,
  duplicates,
  hasMore,
}: {
  cards: number;
  shown: number;
  offers?: number;
  duplicates?: number;
  hasMore: boolean;
}) {
  const dups = Math.max(0, duplicates ?? 0);
  const offerTotal = offers ?? cards;
  const moreHint = hasMore && shown < cards && (
    <span className="hidden sm:inline"> · показано {shown}</span>
  );

  if (!hasMore && dups > 0 && offerTotal > cards) {
    return (
      <>
        Знайдено{" "}
        <strong className="text-ink">{offerTotal.toLocaleString("uk-UA")}</strong>{" "}
        {ukPlural(offerTotal, "пропозицію", "пропозиції", "пропозицій")}
        {" · "}
        {dups.toLocaleString("uk-UA")} {ukPlural(dups, "дубль", "дублі", "дублів")}
        {" · "}
        {cards.toLocaleString("uk-UA")} {ukPlural(cards, "картка", "картки", "карток")}
        {moreHint}
      </>
    );
  }

  return (
    <>
      Знайдено <strong className="text-ink">{cards.toLocaleString("uk-UA")}</strong>
      {moreHint}
    </>
  );
}
