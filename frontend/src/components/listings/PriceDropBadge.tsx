"use client";

import { cn } from "@/lib/utils";
import { formatDropPercent } from "@/lib/listing-price-drop";

type Props = {
  dropPercent: number;
  /** Компактний оверлей на фото картки. */
  variant?: "overlay" | "pill" | "label";
  className?: string;
};

/** Єдиний бейдж зниження ціни для карток, сповіщень і сторінки авто. */
export function PriceDropBadge({ dropPercent, variant = "pill", className }: Props) {
  const label = `−${formatDropPercent(dropPercent)}%`;

  if (variant === "overlay") {
    return (
      <span
        className={cn(
          "rounded-full bg-rose-600 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-white shadow-sm",
          className,
        )}
      >
        {label}
      </span>
    );
  }

  if (variant === "label") {
    return (
      <span
        className={cn(
          "inline-flex rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-rose-700",
          className,
        )}
      >
        Ціну знижено {label}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "rounded-full bg-rose-600 px-2.5 py-1 text-[11px] font-bold text-white",
        className,
      )}
    >
      {label}
    </span>
  );
}
