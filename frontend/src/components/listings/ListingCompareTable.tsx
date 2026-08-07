"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import { IconCompare, IconX } from "@/components/icons";
import { CompareToolbar, ListingCompareMobile } from "@/components/listings/ListingCompareMobile";
import { useAuth } from "@/contexts/AuthProvider";
import {
  buildCompareRows,
  filterDifferentRows,
} from "@/lib/listing-compare-rows";
import { formatListingPrice, resolveDisplayCurrency } from "@/lib/display-currency";
import { cn } from "@/lib/utils";
import type { Listing } from "@/types/api";

type ViewMode = "all" | "diff";

type Props = {
  listings: Listing[];
  onRemove?: (id: string) => void;
  className?: string;
};

function CompareHeaderCell({
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
    <th className="min-w-[160px] max-w-[220px] border-b border-border/60 bg-white px-3 py-4 align-top font-normal sm:min-w-[180px]">
      <div className="relative mx-auto aspect-[4/3] w-full max-w-[200px] overflow-hidden rounded-xl bg-surface">
        {image ? (
          <Image
            src={image}
            alt={listing.title}
            fill
            className="object-cover"
            sizes="200px"
            unoptimized
          />
        ) : (
          <div className="flex h-full items-center justify-center text-[11px] text-muted">Без фото</div>
        )}
        {onRemove && (
          <button
            type="button"
            onClick={() => onRemove(listing.id)}
            className="absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center rounded-full bg-ink/70 text-white hover:bg-ink"
            aria-label="Прибрати з порівняння"
          >
            <IconX size={14} />
          </button>
        )}
      </div>
      <p className="mt-2 line-clamp-2 text-[12px] font-bold leading-snug text-ink sm:text-[13px]">
        {listing.title}
      </p>
      <p className="mt-1 text-[15px] font-black text-ink">{price}</p>
      {listing.url && (
        <a
          href={listing.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-block text-[11px] font-semibold text-emerald-dark hover:underline"
        >
          Відкрити оголошення →
        </a>
      )}
    </th>
  );
}

function ListingCompareDesktopTable({
  listings,
  onRemove,
  rows,
  displayCurrency,
}: {
  listings: Listing[];
  onRemove?: (id: string) => void;
  rows: ReturnType<typeof buildCompareRows>;
  displayCurrency: ReturnType<typeof resolveDisplayCurrency>;
}) {
  return (
    <div className="hidden overflow-x-auto rounded-2xl border border-border/60 bg-white md:block">
      <table className="w-full min-w-[640px] border-collapse text-[13px]">
        <thead>
          <tr>
            <th className="sticky left-0 z-[1] w-[120px] min-w-[120px] border-b border-r border-border/60 bg-surface/90 px-3 py-4 text-left text-[11px] font-bold uppercase tracking-wide text-muted backdrop-blur-sm">
              Параметр
            </th>
            {listings.map(listing => (
              <CompareHeaderCell
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
            rows.map(row => (
              <tr key={row.key} className="border-b border-border/40 last:border-0">
                <th className="sticky left-0 z-[1] border-r border-border/40 bg-surface/80 px-3 py-3 text-left text-[12px] font-semibold text-muted backdrop-blur-sm">
                  {row.label}
                </th>
                {row.values.map((value, index) => {
                  const listing = listings[index];
                  const isPrice = row.key === "price";
                  const highlighted = row.highlightIndexes?.includes(index);
                  return (
                    <td
                      key={`${row.key}-${listing?.id ?? index}`}
                      className={cn(
                        "px-3 py-3 align-top text-[12px] leading-relaxed sm:text-[13px]",
                        isPrice ? "font-black text-ink" : "text-ink/90",
                        row.key === "vin" && "font-mono text-[11px]",
                        highlighted && "bg-emerald/10 font-semibold text-emerald-dark",
                      )}
                    >
                      {value}
                      {highlighted && row.key === "price" && (
                        <span className="mt-1 block text-[10px] font-bold uppercase tracking-wide text-emerald-dark">
                          Найнижча
                        </span>
                      )}
                      {highlighted && row.key === "mileage" && (
                        <span className="mt-1 block text-[10px] font-bold uppercase tracking-wide text-emerald-dark">
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
  );
}

export function ListingCompareTable({ listings, onRemove, className }: Props) {
  const { user } = useAuth();
  const displayCurrency = resolveDisplayCurrency(user?.preferred_currency);
  const includePremiumFields = Boolean(user && user.plan !== "free");
  const [viewMode, setViewMode] = useState<ViewMode>("all");

  const allRows = useMemo(
    () => buildCompareRows(listings, displayCurrency, { includePremiumFields }),
    [listings, displayCurrency, includePremiumFields],
  );

  const rows = useMemo(
    () => (viewMode === "diff" ? filterDifferentRows(allRows) : allRows),
    [allRows, viewMode],
  );

  if (listings.length === 0) {
    return null;
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div className="hidden md:block">
        <CompareToolbar
          count={listings.length}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          includePremiumFields={includePremiumFields}
        />
      </div>

      <ListingCompareMobile
        listings={listings}
        onRemove={onRemove}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      <ListingCompareDesktopTable
        listings={listings}
        onRemove={onRemove}
        rows={rows}
        displayCurrency={displayCurrency}
      />
    </div>
  );
}

export function CompareEmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-surface/40 px-6 py-12 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald/10 text-emerald-dark">
        <IconCompare size={24} />
      </div>
      <h2 className="mt-4 text-[17px] font-bold text-ink">Порівняння порожнє</h2>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-muted">
        У пошуку натисніть іконку ваг на картці авто — можна додати до {4} оголошень і
        порівняти ціну, пробіг, двигун та інші параметри.
      </p>
      <Link
        href="/app/dashboard"
        className="mt-5 inline-flex min-h-11 items-center rounded-xl bg-emerald px-5 py-2.5 text-[13px] font-bold text-white hover:bg-emerald-dark"
      >
        Перейти до пошуку
      </Link>
    </div>
  );
}
