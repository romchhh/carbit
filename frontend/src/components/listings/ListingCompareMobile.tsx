"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo } from "react";
import { IconCompare, IconX } from "@/components/icons";
import { useAuth } from "@/contexts/AuthProvider";
import {
  buildCompareRows,
  filterDifferentRows,
  type CompareRow,
} from "@/lib/listing-compare-rows";
import { formatListingPrice, resolveDisplayCurrency } from "@/lib/display-currency";
import { cn } from "@/lib/utils";
import type { Listing } from "@/types/api";

type ViewMode = "all" | "diff";

type Props = {
  listings: Listing[];
  onRemove?: (id: string) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  className?: string;
};

function shortListingLabel(listing: Listing): string {
  const brandModel = [listing.brand, listing.model].filter(Boolean).join(" ").trim();
  if (brandModel) return brandModel;
  const title = listing.title?.trim();
  if (!title) return "Авто";
  return title.length > 28 ? `${title.slice(0, 28)}…` : title;
}

function highlightBadge(row: CompareRow, index: number): string | null {
  if (!row.highlightIndexes?.includes(index)) return null;
  if (row.key === "price") return "Найнижча";
  if (row.key === "mileage") return "Менший пробіг";
  return "Краще";
}

function ParameterValues({
  row,
  listings,
}: {
  row: CompareRow;
  listings: Listing[];
}) {
  const stacked = listings.length >= 3;

  if (stacked) {
    return (
      <div className="divide-y divide-border/40">
        {row.values.map((value, index) => {
          const listing = listings[index];
          const highlighted = row.highlightIndexes?.includes(index);
          const badge = highlightBadge(row, index);

          return (
            <div
              key={`${row.key}-${listing?.id ?? index}`}
              className={cn("px-3.5 py-3", highlighted && "bg-emerald/8")}
            >
              <div className="flex items-start justify-between gap-3">
                <p className="min-w-0 flex-1 truncate text-[11px] font-semibold text-muted">
                  {shortListingLabel(listing)}
                </p>
                {badge && (
                  <span className="shrink-0 rounded-full bg-emerald/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-dark">
                    {badge}
                  </span>
                )}
              </div>
              <p
                className={cn(
                  "mt-1 break-words text-[14px] leading-snug",
                  row.key === "price" ? "font-black text-ink" : "font-medium text-ink/90",
                  row.key === "vin" && "font-mono text-[11px]",
                  highlighted && "text-emerald-dark",
                )}
              >
                {value}
              </p>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className={cn("grid gap-px bg-border/40 p-px", gridClassForCount(listings.length))}>
      {row.values.map((value, index) => {
        const listing = listings[index];
        const highlighted = row.highlightIndexes?.includes(index);
        const badge = highlightBadge(row, index);

        return (
          <div
            key={`${row.key}-${listing?.id ?? index}`}
            className={cn("min-w-0 bg-white px-3 py-3", highlighted && "bg-emerald/8")}
          >
            <p className="truncate text-[10px] font-semibold uppercase tracking-wide text-muted">
              {shortListingLabel(listing)}
            </p>
            <p
              className={cn(
                "mt-1 break-words text-[13px] leading-snug",
                row.key === "price" ? "font-black text-ink" : "font-medium text-ink/90",
                row.key === "vin" && "font-mono text-[11px]",
                highlighted && "text-emerald-dark",
              )}
            >
              {value}
            </p>
            {badge && (
              <span className="mt-1.5 inline-flex rounded-full bg-emerald/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-dark">
                {badge}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function gridClassForCount(count: number): string {
  if (count <= 1) return "grid-cols-1";
  return "grid-cols-2";
}

export function ListingCompareMobile({
  listings,
  onRemove,
  viewMode,
  onViewModeChange,
  className,
}: Props) {
  const { user } = useAuth();
  const displayCurrency = resolveDisplayCurrency(user?.preferred_currency);
  const includePremiumFields = Boolean(user && user.plan !== "free");

  const allRows = useMemo(
    () => buildCompareRows(listings, displayCurrency, { includePremiumFields }),
    [listings, displayCurrency, includePremiumFields],
  );

  const rows = useMemo(
    () => (viewMode === "diff" ? filterDifferentRows(allRows) : allRows),
    [allRows, viewMode],
  );

  if (listings.length === 0) return null;

  return (
    <div className={cn("space-y-4 md:hidden", className)}>
      <CompareToolbar
        count={listings.length}
        viewMode={viewMode}
        onViewModeChange={onViewModeChange}
        includePremiumFields={includePremiumFields}
        compact
      />

      <div className="-mx-1 flex gap-3 overflow-x-auto px-1 pb-1 [-ms-overflow-style:none] [scrollbar-width:none] snap-x snap-mandatory [&::-webkit-scrollbar]:hidden">
        {listings.map(listing => {
          const image = listing.images?.[0];
          const price = formatListingPrice(
            Number(listing.price) || 0,
            listing.currency,
            displayCurrency,
            listing.source_data,
          );

          return (
            <article
              key={listing.id}
              className="w-[min(78vw,280px)] shrink-0 snap-center overflow-hidden rounded-2xl border border-border/70 bg-white shadow-sm"
            >
              <div className="relative aspect-[4/3] bg-surface">
                {image ? (
                  <Image
                    src={image}
                    alt={listing.title}
                    fill
                    className="object-cover"
                    sizes="280px"
                    unoptimized
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-[12px] text-muted">
                    Без фото
                  </div>
                )}
                {onRemove && (
                  <button
                    type="button"
                    onClick={() => onRemove(listing.id)}
                    className="absolute right-2 top-2 flex h-8 w-8 items-center justify-center rounded-full bg-ink/75 text-white active:scale-95"
                    aria-label="Прибрати з порівняння"
                  >
                    <IconX size={15} />
                  </button>
                )}
              </div>
              <div className="space-y-2 p-3">
                <p className="line-clamp-2 text-[13px] font-bold leading-snug text-ink">
                  {listing.title}
                </p>
                <p className="text-[18px] font-black tracking-tight text-ink">{price}</p>
                {listing.url && (
                  <a
                    href={listing.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex min-h-10 items-center text-[12px] font-semibold text-emerald-dark"
                  >
                    Відкрити оголошення →
                  </a>
                )}
              </div>
            </article>
          );
        })}
      </div>

      <div className="space-y-2.5">
        {rows.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-border bg-surface/40 px-4 py-8 text-center text-[13px] text-muted">
            Усі обрані авто мають однакові характеристики в доступних полях.
          </p>
        ) : (
          rows.map(row => (
            <section
              key={row.key}
              className="overflow-hidden rounded-2xl border border-border/60 bg-white"
            >
              <div className="border-b border-border/50 bg-surface/60 px-3.5 py-2.5">
                <h3 className="text-[11px] font-bold uppercase tracking-wide text-muted">
                  {row.label}
                </h3>
              </div>
              <ParameterValues row={row} listings={listings} />
            </section>
          ))
        )}
      </div>
    </div>
  );
}

type ToolbarProps = {
  count: number;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  includePremiumFields: boolean;
  compact?: boolean;
};

export function CompareToolbar({
  count,
  viewMode,
  onViewModeChange,
  includePremiumFields,
  compact = false,
}: ToolbarProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center",
        compact && "gap-2.5",
      )}
    >
      <span className="inline-flex items-center gap-1.5 text-[13px] font-bold text-ink">
        <IconCompare size={16} className="text-emerald-dark" />
        {count} авто
      </span>
      <div className="flex rounded-xl border border-border/70 bg-surface/50 p-0.5">
        <button
          type="button"
          onClick={() => onViewModeChange("all")}
          className={cn(
            "min-h-10 flex-1 rounded-lg px-3 py-2 text-[12px] font-semibold transition sm:flex-none sm:py-1.5",
            viewMode === "all" ? "bg-white text-ink shadow-sm" : "text-muted hover:text-ink",
          )}
        >
          Усі характеристики
        </button>
        <button
          type="button"
          onClick={() => onViewModeChange("diff")}
          className={cn(
            "min-h-10 flex-1 rounded-lg px-3 py-2 text-[12px] font-semibold transition sm:flex-none sm:py-1.5",
            viewMode === "diff" ? "bg-white text-ink shadow-sm" : "text-muted hover:text-ink",
          )}
        >
          Відмінності
        </button>
      </div>
      {includePremiumFields ? (
        <span className="text-[11px] text-emerald-dark">+ AUTO.RIA деталі</span>
      ) : (
        <Link
          href="/app/billing"
          className="text-[11px] font-semibold leading-relaxed text-muted hover:text-emerald-dark"
        >
          Колір і комплектація — на платному тарифі
        </Link>
      )}
    </div>
  );
}
