"use client";

import { useState } from "react";
import { VinCheckPanel } from "@/components/listings/VinCheckPanel";
import { VinCheckSummary } from "@/components/listings/VinCheckSummary";
import { cn } from "@/lib/utils";
import { useVinCheckCache } from "@/hooks/useVinCheckCache";
import { getVinCheckUrl, resolveListingVin } from "@/lib/vin-check";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing;
  className?: string;
  size?: "sm" | "md";
  /** Компактний звіт під кнопкою (для картки оголошення). */
  showSummary?: boolean;
};

export function VinCheckButton({ listing, className, size = "sm", showSummary = false }: Props) {
  const [open, setOpen] = useState(false);
  const vin = resolveListingVin(listing);
  const cached = useVinCheckCache(vin);
  const fallbackUrl = getVinCheckUrl(listing);

  const openPanel = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setOpen(true);
  };

  // Показуємо кнопку лише коли є VIN-код.
  if (!vin) return null;

  return (
    <>
      <div className={cn(showSummary && "flex w-full flex-col gap-2")}>
        <button
          type="button"
          onClick={openPanel}
          className={cn(
            "inline-flex items-center justify-center rounded-full border border-emerald/30 bg-emerald/10 font-semibold text-emerald-dark transition-colors hover:border-emerald/50 hover:bg-emerald/15",
            size === "sm" ? "px-3 py-1.5 text-[11px]" : "px-4 py-2 text-[13px]",
            className,
          )}
        >
          {cached ? "Звіт VIN" : "Перевірити за VIN"}
        </button>
        {showSummary && cached && (
          <VinCheckSummary
            cached={cached}
            onClick={e => {
              e.stopPropagation();
              openPanel();
            }}
          />
        )}
      </div>
      <VinCheckPanel
        vin={vin}
        listingId={listing.id}
        fallbackUrl={fallbackUrl}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
