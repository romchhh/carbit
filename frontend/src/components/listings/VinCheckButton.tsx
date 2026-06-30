"use client";

import { cn } from "@/lib/utils";
import { getVinCheckUrl } from "@/lib/vin-check";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing;
  className?: string;
  size?: "sm" | "md";
};

export function VinCheckButton({ listing, className, size = "sm" }: Props) {
  const href = getVinCheckUrl(listing);
  if (!href) return null;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onClick={e => e.stopPropagation()}
      className={cn(
        "inline-flex items-center justify-center rounded-full border border-emerald/30 bg-emerald/10 font-semibold text-emerald-dark transition-colors hover:border-emerald/50 hover:bg-emerald/15",
        size === "sm" ? "px-3 py-1.5 text-[11px]" : "px-4 py-2 text-[13px]",
        className,
      )}
    >
      Перевірити за VIN
    </a>
  );
}
