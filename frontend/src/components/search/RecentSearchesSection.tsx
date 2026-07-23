"use client";

import { useEffect, useState } from "react";
import { IconArrowRight, IconClock, IconSearch } from "@/components/icons";
import { AppSection } from "@/components/layout/AppPage";
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

export function RecentSearchesSection({ limit = 8, className, onSelect }: Props) {
  const [items, setItems] = useState<RecentSearchEntry[]>([]);

  useEffect(() => {
    const sync = () => setItems(loadRecentSearches().slice(0, limit));
    sync();
    const eventName = recentSearchesChangedEvent();
    window.addEventListener(eventName, sync);
    return () => window.removeEventListener(eventName, sync);
  }, [limit]);

  if (items.length === 0) return null;

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
        {items.map(entry => {
          const desc = formatSearchDesc(toBackendSearchFilters(entry.filters));
          const when = formatRelativeAt(entry.at);
          return (
            <AppSection
              key={entry.id}
              className="!bg-white p-0 transition-colors hover:border-emerald/35"
            >
              <button
                type="button"
                onClick={() => onSelect(entry)}
                className="flex w-full items-center gap-3 px-3 py-3 text-left sm:gap-4 sm:px-4 sm:py-3.5"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface text-muted ring-1 ring-border/70">
                  <IconSearch size={16} />
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
                <IconArrowRight size={16} className="shrink-0 text-muted" />
              </button>
            </AppSection>
          );
        })}
      </div>
    </section>
  );
}
