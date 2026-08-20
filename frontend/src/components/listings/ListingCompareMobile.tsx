"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo } from "react";
import { IconCompare, IconX } from "@/components/icons";
import { useAuth } from "@/contexts/AuthProvider";
import {
  buildCompareRows,
  filterDifferentRows,
} from "@/lib/listing-compare-rows";
import { formatListingPrice, resolveDisplayCurrency } from "@/lib/display-currency";
import { openExternalUrl } from "@/lib/open-external";
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

function shortTitle(listing: Listing): string {
  const brandModel = [listing.brand, listing.model].filter(Boolean).join(" ").trim();
  if (brandModel) return brandModel.length > 18 ? `${brandModel.slice(0, 18)}…` : brandModel;
  const title = listing.title?.trim() || "Авто";
  return title.length > 18 ? `${title.slice(0, 18)}…` : title;
}

/** Ширина колонки авто: ~3 штуки + «Параметр» на типовому телефоні */
const MOBILE_COL =
  "w-[calc((100vw-4.5rem)/3)] min-w-[96px] max-w-[118px]";
const MOBILE_STICKY_BASE =
  "sticky left-0 w-14 min-w-[3.5rem] max-w-[3.5rem]";

function MobileHeaderCell({
  listing,
  onRemove,
  displayCurrency,
}: {
  listing: Listing;
  onRemove?: (id: string) => void;
  displayCurrency: ReturnType<typeof resolveDisplayCurrency>;
}) {
  const image = listing.images?.[0];
  const price = formatListingPrice(
    Number(listing.price) || 0,
    listing.currency,
    displayCurrency,
    listing.source_data,
  );

  return (
    <th className={cn(MOBILE_COL, "border-b border-border/60 bg-white px-1.5 py-2.5 align-top font-normal")}>
      <div className="relative mx-auto aspect-[4/3] w-full overflow-hidden rounded-lg bg-surface">
        {image ? (
          <Image
            src={image}
            alt={listing.title}
            fill
            className="object-cover"
            sizes="110px"
            unoptimized
          />
        ) : (
          <div className="flex h-full items-center justify-center text-[10px] text-muted">Без фото</div>
        )}
        {onRemove && (
          <button
            type="button"
            onClick={() => onRemove(listing.id)}
            className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-ink/75 text-white active:scale-95"
            aria-label="Прибрати з порівняння"
          >
            <IconX size={12} />
          </button>
        )}
      </div>
      <p className="mt-1.5 line-clamp-2 text-[11px] font-bold leading-snug text-ink">
        {shortTitle(listing)}
      </p>
      <p className="mt-0.5 text-[12px] font-black tracking-tight text-ink">{price}</p>
      {listing.url && (
        <a
          href={listing.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={e => openExternalUrl(listing.url, e)}
          className="mt-1 inline-flex min-h-7 items-center text-[10px] font-semibold text-emerald-dark"
        >
          Відкрити →
        </a>
      )}
    </th>
  );
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
    <div className={cn("space-y-3 md:hidden", className)}>
      <CompareToolbar
        count={listings.length}
        viewMode={viewMode}
        onViewModeChange={onViewModeChange}
        includePremiumFields={includePremiumFields}
        compact
      />

      {listings.length > 3 && (
        <p className="px-0.5 text-[11px] text-muted">Гортайте вбік — ще {listings.length - 3} авто</p>
      )}

      <div className="-mx-2.5 overflow-x-auto overscroll-x-contain border-y border-border/60 bg-white sm:mx-0 sm:rounded-2xl sm:border">
        <table className="w-max min-w-full border-collapse text-[12px]">
          <thead>
            <tr>
              <th
                className={cn(
                  MOBILE_STICKY_BASE,
                  "z-[2] border-b border-r border-border/60 bg-surface px-1 py-2.5 text-left text-[9px] font-bold uppercase leading-tight tracking-wide text-muted shadow-[3px_0_10px_-5px_rgba(10,12,14,0.18)]",
                )}
              >
                Параметр
              </th>
              {listings.map(listing => (
                <MobileHeaderCell
                  key={listing.id}
                  listing={listing}
                  onRemove={onRemove}
                  displayCurrency={displayCurrency}
                />
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={listings.length + 1}
                  className="px-4 py-10 text-center text-[13px] text-muted"
                >
                  Усі обрані авто мають однакові характеристики в доступних полях.
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr
                  key={row.key}
                  className={cn(
                    "border-b border-border/40 last:border-0",
                    rowIndex % 2 === 1 && "bg-surface/25",
                  )}
                >
                  <th
                    className={cn(
                      MOBILE_STICKY_BASE,
                      "z-[1] border-r border-border/40 bg-surface px-1 py-2.5 text-left text-[10px] font-semibold leading-snug text-muted shadow-[3px_0_10px_-5px_rgba(10,12,14,0.14)]",
                    )}
                  >
                    {row.label}
                  </th>
                  {row.values.map((value, index) => {
                    const listing = listings[index];
                    const highlighted = row.highlightIndexes?.includes(index);
                    return (
                      <td
                        key={`${row.key}-${listing?.id ?? index}`}
                        className={cn(
                          MOBILE_COL,
                          "px-1.5 py-2.5 align-top text-[11px] leading-snug",
                          row.key === "price" ? "font-black text-ink" : "text-ink/90",
                          row.key === "vin" && "break-all font-mono text-[9px]",
                          highlighted && "bg-emerald/10 font-semibold text-emerald-dark",
                        )}
                      >
                        {value}
                        {highlighted && row.key === "price" && (
                          <span className="mt-0.5 block text-[9px] font-bold uppercase tracking-wide text-emerald-dark">
                            Найнижча
                          </span>
                        )}
                        {highlighted && row.key === "mileage" && (
                          <span className="mt-0.5 block text-[9px] font-bold uppercase tracking-wide text-emerald-dark">
                            Менший пробіг
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
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
