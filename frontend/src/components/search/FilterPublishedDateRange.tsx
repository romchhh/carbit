"use client";

import { IosToggle } from "@/components/ui/IosToggle";
import type { PublishedWithinDaysValue } from "@/lib/search-catalog";
import { formatPublishedFilterSummary } from "@/lib/published-date-filter";
import type { SearchFreshness } from "@/lib/search-preview";

type Props = {
  freshness: SearchFreshness;
  publishedWithinDays: PublishedWithinDaysValue;
  publishedFrom: string;
  publishedTo: string;
  onFreshnessChange: (freshness: SearchFreshness) => void;
  onChange: (patch: {
    publishedWithinDays?: PublishedWithinDaysValue;
    publishedFrom?: string;
    publishedTo?: string;
  }) => void;
};

type ListingAgeMode = "all" | "fresh" | "15" | "30";

function resolveListingAgeMode(
  freshness: SearchFreshness,
  publishedWithinDays: PublishedWithinDaysValue,
): ListingAgeMode {
  if (freshness === "new") return "fresh";
  if (publishedWithinDays === "15") return "15";
  if (publishedWithinDays === "30") return "30";
  return "all";
}

export function FilterPublishedDateRange({
  freshness,
  publishedWithinDays,
  publishedFrom,
  publishedTo,
  onFreshnessChange,
  onChange,
}: Props) {
  const mode = resolveListingAgeMode(freshness, publishedWithinDays);
  const summary = formatPublishedFilterSummary(
    publishedWithinDays,
    publishedFrom,
    publishedTo,
    freshness,
  );

  const clearPublishedRange = () => {
    onChange({ publishedWithinDays: "", publishedFrom: "", publishedTo: "" });
  };

  const setMode = (next: ListingAgeMode) => {
    if (next === "fresh") {
      onFreshnessChange("new");
      clearPublishedRange();
      return;
    }
    onFreshnessChange("all");
    if (next === "15" || next === "30") {
      onChange({ publishedWithinDays: next, publishedFrom: "", publishedTo: "" });
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
          <span className="text-[13px] font-medium text-ink">Тільки свіжі оголошення</span>
          <IosToggle
            checked={mode === "fresh"}
            aria-label="Тільки свіжі оголошення"
            onChange={() => toggleMode("fresh")}
          />
        </div>
        <div className="flex items-center justify-between gap-3 rounded-lg px-0.5 py-1">
          <span className="text-[13px] font-medium text-ink">Показувати від 15 днів</span>
          <IosToggle
            checked={mode === "15"}
            aria-label="Показувати оголошення від 15 днів"
            onChange={() => toggleMode("15")}
          />
        </div>
        <div className="flex items-center justify-between gap-3 rounded-lg px-0.5 py-1">
          <span className="text-[13px] font-medium text-ink">Показувати від 30 днів</span>
          <IosToggle
            checked={mode === "30"}
            aria-label="Показувати оголошення від 30 днів"
            onChange={() => toggleMode("30")}
          />
        </div>
      </div>
    </div>
  );
}
