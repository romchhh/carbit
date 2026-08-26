"use client";

import { IosToggle } from "@/components/ui/IosToggle";
import type { PublishedOlderThanDaysValue } from "@/lib/search-catalog";
import { formatPublishedFilterSummary } from "@/lib/published-date-filter";
import type { SearchFreshness } from "@/lib/search-preview";

type Props = {
  freshness: SearchFreshness;
  publishedOlderThanDays: PublishedOlderThanDaysValue;
  publishedFrom: string;
  publishedTo: string;
  onFreshnessChange: (freshness: SearchFreshness) => void;
  onChange: (patch: {
    publishedOlderThanDays?: PublishedOlderThanDaysValue;
    publishedFrom?: string;
    publishedTo?: string;
  }) => void;
};

type ListingAgeMode = "all" | "fresh" | "15" | "30";

function resolveListingAgeMode(
  freshness: SearchFreshness,
  publishedOlderThanDays: PublishedOlderThanDaysValue,
): ListingAgeMode {
  if (freshness === "new") return "fresh";
  if (publishedOlderThanDays === "15") return "15";
  if (publishedOlderThanDays === "30") return "30";
  return "all";
}

export function FilterPublishedDateRange({
  freshness,
  publishedOlderThanDays,
  publishedFrom,
  publishedTo,
  onFreshnessChange,
  onChange,
}: Props) {
  const mode = resolveListingAgeMode(freshness, publishedOlderThanDays);
  const summary = formatPublishedFilterSummary(
    publishedOlderThanDays,
    publishedFrom,
    publishedTo,
    freshness,
  );

  const clearPublishedRange = () => {
    onChange({ publishedOlderThanDays: "", publishedFrom: "", publishedTo: "" });
  };

  const setMode = (next: ListingAgeMode) => {
    if (next === "fresh") {
      onFreshnessChange("new");
      clearPublishedRange();
      return;
    }
    onFreshnessChange("all");
    if (next === "15" || next === "30") {
      onChange({ publishedOlderThanDays: next, publishedFrom: "", publishedTo: "" });
      return;
    }
    clearPublishedRange();
  };

  const toggleMode = (target: Exclude<ListingAgeMode, "all">) => {
    setMode(mode === target ? "all" : target);
  };

  const clearAll = () => {
    setMode("all");
  };

  return (
    <div className="space-y-3">
      {summary ? (
        <div className="flex items-start justify-between gap-3">
          <div className="rounded-lg border border-emerald/20 bg-emerald/[0.06] px-3 py-2 text-[12px] font-medium text-emerald-dark">
            {summary}
          </div>
          <button
            type="button"
            onClick={clearAll}
            className="shrink-0 rounded-full border border-border px-2.5 py-1 text-[11px] font-medium text-muted transition-colors hover:border-red-300 hover:text-red-600"
          >
            Скинути
          </button>
        </div>
      ) : null}

      <div className="space-y-2 rounded-xl border border-border/70 bg-white p-3">
        <div className="flex items-center justify-between gap-3 rounded-lg px-0.5 py-1">
          <div className="min-w-0">
            <span className="text-[13px] font-medium text-ink">Тільки свіжі оголошення</span>
            <p className="text-[11px] text-muted">За останні 7 днів</p>
          </div>
          <IosToggle
            checked={mode === "fresh"}
            aria-label="Тільки свіжі оголошення за останні 7 днів"
            onChange={() => toggleMode("fresh")}
          />
        </div>
        <div className="flex items-center justify-between gap-3 rounded-lg px-0.5 py-1">
          <div className="min-w-0">
            <span className="text-[13px] font-medium text-ink">Від 15 днів</span>
            <p className="text-[11px] text-muted">На ринку більше 15 днів</p>
          </div>
          <IosToggle
            checked={mode === "15"}
            aria-label="Показувати оголошення на ринку більше 15 днів"
            onChange={() => toggleMode("15")}
          />
        </div>
        <div className="flex items-center justify-between gap-3 rounded-lg px-0.5 py-1">
          <div className="min-w-0">
            <span className="text-[13px] font-medium text-ink">Від 30 днів</span>
            <p className="text-[11px] text-muted">На ринку більше 30 днів</p>
          </div>
          <IosToggle
            checked={mode === "30"}
            aria-label="Показувати оголошення на ринку більше 30 днів"
            onChange={() => toggleMode("30")}
          />
        </div>
      </div>
    </div>
  );
}
