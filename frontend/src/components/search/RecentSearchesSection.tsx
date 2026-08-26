"use client";

import { useEffect, useState } from "react";
import { IconClock } from "@/components/icons";
import { ListingPhoto } from "@/components/listings/ListingPhoto";
import { DashboardScrollRow } from "@/components/layout/DashboardScrollRow";
import { formatSearchDesc } from "@/lib/format-search-desc";
import {
  loadRecentSearches,
  recentSearchesChangedEvent,
  type RecentSearchEntry,
} from "@/lib/recent-searches";
import { toBackendSearchFilters } from "@/lib/search-filters-api";
import { cn } from "@/lib/utils";

type Props = {
  limit?: number;
  className?: string;
  onSelect: (entry: RecentSearchEntry) => void;
  layout?: "list" | "row";
};

function formatRelativeAt(iso: string): string {
  const ts = Date.parse(iso);
  if (!Number.isFinite(ts)) return "";
  const diffMs = Date.now() - ts;
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "щойно";
  if (mins < 60) return `${mins} хв тому`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} год тому`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} д. тому`;
  return new Date(ts).toLocaleDateString("uk-UA", {
    day: "numeric",
    month: "short",
  });
}

function RecentSearchCard({
  entry,
  onSelect,
  compact,
}: {
  entry: RecentSearchEntry;
  onSelect: (entry: RecentSearchEntry) => void;
  compact?: boolean;
}) {
  const desc = formatSearchDesc(toBackendSearchFilters(entry.filters));
  const when = formatRelativeAt(entry.at);

  if (compact) {
    return (
      <button
        type="button"
        onClick={() => onSelect(entry)}
        className="flex w-[252px] shrink-0 flex-col overflow-hidden rounded-xl border border-border/70 bg-white text-left transition-all hover:border-emerald/35 hover:shadow-md hover:shadow-emerald/5"
      >
        <span className="relative h-[108px] w-full bg-surface">
          <ListingPhoto
            src={entry.previewImage}
            alt=""
            sizes="252px"
            logoClassName="h-7 opacity-70"
          />
        </span>
        <span className="flex min-h-[88px] flex-col gap-1 p-3">
          <span className="line-clamp-1 text-[14px] font-semibold text-ink">{entry.name}</span>
          <span className="line-clamp-2 text-[11px] leading-snug text-muted">{desc}</span>
          <span className="mt-auto flex flex-wrap items-center gap-1.5 text-[10px] text-muted">
            {entry.freshness === "new" ? (
              <span className="rounded-md bg-emerald-light/70 px-1.5 py-0.5 font-semibold text-emerald-dark">
                Свіжі
              </span>
            ) : null}
            {when ? (
              <span className="inline-flex items-center gap-1">
                <IconClock size={10} />
                {when}
              </span>
            ) : null}
          </span>
        </span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onSelect(entry)}
      className="flex w-full items-center gap-3 rounded-xl border border-border/70 bg-white px-3 py-3 text-left transition-colors hover:border-emerald/35 sm:gap-4 sm:px-4 sm:py-3.5"
    >
      <span className="relative h-12 w-[4.25rem] shrink-0 overflow-hidden rounded-xl bg-surface ring-1 ring-border/70 sm:h-14 sm:w-24">
        <ListingPhoto
          src={entry.previewImage}
          alt=""
          sizes="96px"
          logoClassName="h-5 opacity-70"
        />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[14px] font-semibold text-ink sm:text-[15px]">
          {entry.name}
        </span>
        <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-muted sm:text-[12px]">
          <span className="line-clamp-1">{desc}</span>
          {entry.freshness === "new" && (
            <span className="rounded-md bg-emerald-light/60 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-dark">
              Свіжі
            </span>
          )}
          {when && (
            <span className="inline-flex items-center gap-1 text-muted/80">
              <IconClock size={11} />
              {when}
            </span>
          )}
        </span>
      </span>
    </button>
  );
}

export function RecentSearchesSection({
  limit = 8,
  className,
  onSelect,
  layout = "row",
}: Props) {
  const [items, setItems] = useState<RecentSearchEntry[]>([]);

  useEffect(() => {
    const sync = () => setItems(loadRecentSearches().slice(0, limit));
    sync();
    const eventName = recentSearchesChangedEvent();
    window.addEventListener(eventName, sync);
    return () => window.removeEventListener(eventName, sync);
  }, [limit]);

  if (items.length === 0) return null;

  if (layout === "row") {
    return (
      <DashboardScrollRow
        title="Останні пошуки"
        description="Натисніть, щоб знову підставити фільтри"
        className={className}
      >
        {items.map(entry => (
          <RecentSearchCard key={entry.id} entry={entry} onSelect={onSelect} compact />
        ))}
      </DashboardScrollRow>
    );
  }

  return (
    <section className={cn("mt-10", className)}>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h2 className="text-[16px] font-black tracking-tight text-ink sm:text-[18px]">
            Останні пошуки
          </h2>
          <p className="mt-0.5 text-[12px] text-muted sm:text-[13px]">
            Архів ваших запитів — натисніть, щоб підставити фільтри
          </p>
        </div>
      </div>

      <div className="space-y-2.5">
        {items.map(entry => (
          <RecentSearchCard key={entry.id} entry={entry} onSelect={onSelect} />
        ))}
      </div>
    </section>
  );
}
