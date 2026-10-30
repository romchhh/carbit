"use client";

import Image from "next/image";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ListingCreditCalculatorModal } from "@/components/listings/ListingCreditCalculatorModal";
import { BANK_PARTNER_BIZBANK } from "@/lib/brand-assets";
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
  /** Короткий підпис «Кредит» (вузькі картки). */
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
        size={compact ? "sm" : "md"}
        className={cn(
          "justify-center gap-2 border-border/80 bg-white hover:bg-surface",
          fullWidth ? "w-full" : "w-full sm:w-auto",
          className,
        )}
        onClick={e => {
          e.preventDefault();
          e.stopPropagation();
          setOpen(true);
        }}
      >
        <Image
          src={BANK_PARTNER_BIZBANK.src}
          alt=""
          width={4147}
          height={942}
          aria-hidden
          className="h-[14px] w-auto max-w-[72px] shrink-0 object-contain sm:h-4 sm:max-w-[84px]"
        />
        <span className="truncate">{compact ? "Кредит" : "Розрахувати кредит"}</span>
        {teaser && !compact ? (
          <span className="hidden font-normal text-muted lg:inline">· від {teaser}/міс.</span>
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
