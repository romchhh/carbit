"use client";

import { useState } from "react";
import { VinCheckPanel } from "@/components/listings/VinCheckPanel";
import { cn } from "@/lib/utils";
import { getVinCheckUrl, resolveListingVin } from "@/lib/vin-check";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing;
  className?: string;
  size?: "sm" | "md";
};

export function VinCheckButton({ listing, className, size = "sm" }: Props) {
  const [open, setOpen] = useState(false);
  const vin = resolveListingVin(listing);
  const fallbackUrl = getVinCheckUrl(listing);

  // Показуємо кнопку якщо є VIN (База ДАІ) або хоча б зовнішній fallback.
  if (!vin && !fallbackUrl) return null;

  return (
    <>
      <button
        type="button"
        onClick={e => {
          e.stopPropagation();
          setOpen(true);
        }}
        className={cn(
          "inline-flex items-center justify-center rounded-full border border-emerald/30 bg-emerald/10 font-semibold text-emerald-dark transition-colors hover:border-emerald/50 hover:bg-emerald/15",
          size === "sm" ? "px-3 py-1.5 text-[11px]" : "px-4 py-2 text-[13px]",
          className,
        )}
      >
        Перевірити за VIN
      </button>
      <VinCheckPanel
        vin={vin}
        fallbackUrl={fallbackUrl}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
