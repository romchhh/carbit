import { cn } from "@/lib/utils";
import {
  formatDropPercent,
  resolveListingPriceDrop,
  type ListingPriceDrop,
} from "@/lib/listing-price-drop";
import {
  formatListingPrice,
  type DisplayCurrency,
} from "@/lib/display-currency";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing;
  displayCurrency: DisplayCurrency;
  className?: string;
  priceClassName?: string;
  previousClassName?: string;
  badgeClassName?: string;
  showBadge?: boolean;
};

export function ListingPriceDisplay({
  listing,
  displayCurrency,
  className,
  priceClassName,
  previousClassName,
  badgeClassName,
  showBadge = true,
}: Props) {
  const price = Number(listing.price) || 0;
  const currentLabel = formatListingPrice(
    price,
    listing.currency,
    displayCurrency,
    listing.source_data,
  );
  const drop = resolveListingPriceDrop(listing);

  if (!drop) {
    return <span className={cn(className, priceClassName)}>{currentLabel}</span>;
  }

  const previousLabel = formatListingPrice(
    drop.previousPrice,
    listing.currency,
    displayCurrency,
    listing.source_data,
  );

  return (
    <div className={cn("flex flex-col items-start gap-1", className)}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={cn("font-black leading-none text-ink", priceClassName)}>
          {currentLabel}
        </span>
        <span
          className={cn(
            "text-[13px] font-semibold leading-none text-muted line-through decoration-muted/70",
            previousClassName,
          )}
        >
          {previousLabel}
        </span>
      </div>
      {showBadge && (
        <span
          className={cn(
            "inline-flex rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-rose-700",
            badgeClassName,
          )}
        >
          Ціну знижено −{formatDropPercent(drop.dropPercent)}%
        </span>
      )}
    </div>
  );
}

export function listingPriceDropBadge(listing: Listing): ListingPriceDrop | null {
  return resolveListingPriceDrop(listing);
}
