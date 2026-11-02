"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ListingCreditCalculatorModal } from "@/components/listings/ListingCreditCalculatorModal";
import {
  BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT,
  BISBANK_DEFAULT_TERM_MONTHS,
  computeBisbankCreditQuote,
  formatMoneyUah,
  minDownPaymentPercent,
  resolveListingPriceUah,
} from "@/lib/bisbank-credit-calculator";
import type { DisplayCurrency } from "@/lib/display-currency";
import { cn } from "@/lib/utils";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing;
  displayCurrency: DisplayCurrency;
  className?: string;
  /** Короткий підпис на вузьких картках (той самий текст, менший розмір). */
  compact?: boolean;
  /** На всю ширину, як «Перевірити за VIN». */
  fullWidth?: boolean;
};

export function ListingCreditCalculatorTrigger({
  listing,
  displayCurrency,
  className,
  compact = false,
  fullWidth = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const carPriceUah = resolveListingPriceUah(listing);

  const teaser = useMemo(() => {
    if (carPriceUah <= 0) return null;
    const down = Math.max(BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT, minDownPaymentPercent(carPriceUah));
    const quote = computeBisbankCreditQuote({
      carPriceUah,
      downPaymentPercent: down,
      termMonths: BISBANK_DEFAULT_TERM_MONTHS,
    });
    if (!quote.loanValid) return null;
    return formatMoneyUah(quote.monthlyPaymentUah);
  }, [carPriceUah]);

  if (carPriceUah <= 0) return null;

  return (
    <>
      <Button
        type="button"
        variant="secondary"
        size={compact ? "sm" : fullWidth ? "lg" : "md"}
        className={cn(
          "justify-center border-emerald/20 bg-emerald-light/30 text-emerald-dark hover:bg-emerald-light/50 hover:translate-y-0",
          fullWidth ? "flex w-full max-w-none rounded-full" : compact ? "w-auto max-w-full" : "w-full",
          className,
        )}
        onClick={e => {
          e.preventDefault();
          e.stopPropagation();
          setOpen(true);
        }}
      >
        <span className="truncate font-semibold">Авто в кредит</span>
        {teaser && !compact ? (
          <span className="font-normal text-emerald-dark/70">· від {teaser}/міс.</span>
        ) : null}
      </Button>

      <ListingCreditCalculatorModal
        open={open}
        listing={listing}
        displayCurrency={displayCurrency}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
