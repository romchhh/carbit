"use client";

import { ListingCreditCalculatorTrigger } from "@/components/listings/ListingCreditCalculatorTrigger";
import { ListingOpenCta } from "@/components/listings/SourceLinks";
import { VinCheckButton } from "@/components/listings/VinCheckButton";
import { hasVinCheck } from "@/lib/vin-check";
import { resolveListingPriceUah } from "@/lib/bisbank-credit-calculator";
import type { DisplayCurrency } from "@/lib/display-currency";
import { cn } from "@/lib/utils";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing;
  displayCurrency: DisplayCurrency;
  className?: string;
  /** Показувати «Відкрити на …» (сторінка / модалка). */
  showOpenLinks?: boolean;
  openCtaClassName?: string;
  vinSize?: "sm" | "md";
  vinShowSummary?: boolean;
  creditCompact?: boolean;
};

/** «Відкрити на …», кредит БІЗБАНК, перевірка VIN — одним блоком, кнопки на всю ширину. */
export function ListingActions({
  listing,
  displayCurrency,
  className,
  showOpenLinks = false,
  openCtaClassName,
  vinSize = "md",
  vinShowSummary = false,
  creditCompact = false,
}: Props) {
  const showCredit = resolveListingPriceUah(listing) > 0;
  const showVin = hasVinCheck(listing);

  if (!showOpenLinks && !showCredit && !showVin) return null;

  return (
    <div className={cn("flex w-full flex-col gap-2", className)}>
      {showOpenLinks ? (
        <ListingOpenCta listing={listing} className={cn("w-full", openCtaClassName)} />
      ) : null}

      {showCredit ? (
        <ListingCreditCalculatorTrigger
          listing={listing}
          displayCurrency={displayCurrency}
          fullWidth
          compact={creditCompact}
          className="w-full"
        />
      ) : null}

      {showVin ? (
        <VinCheckButton
          listing={listing}
          size={vinSize}
          showSummary={vinShowSummary}
          className="w-full"
        />
      ) : null}
    </div>
  );
}
