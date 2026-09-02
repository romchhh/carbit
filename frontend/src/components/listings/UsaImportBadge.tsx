"use client";

import {
  LISTING_USA_IMPORT_LABEL,
  LISTING_USA_IMPORT_SHORT_LABEL,
} from "@/lib/listing-usa-import";
import { cn } from "@/lib/utils";

type Props = {
  /** Компактний оверлей на фото картки. */
  variant?: "overlay" | "pill" | "label";
  className?: string;
};

/** Позначка «пригнано з США» для карток оголошень. */
export function UsaImportBadge({ variant = "pill", className }: Props) {
  const label = variant === "overlay" ? LISTING_USA_IMPORT_SHORT_LABEL : LISTING_USA_IMPORT_LABEL;

  if (variant === "overlay") {
    return (
      <span
        className={cn(
          "rounded-full bg-indigo-700 px-2.5 py-1 text-[10px] font-bold tracking-wide text-white shadow-sm",
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
          "inline-flex rounded-full bg-indigo-50 px-2.5 py-1 text-[10px] font-bold tracking-wide text-indigo-900 ring-1 ring-indigo-200/80",
          className,
        )}
      >
        {label}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-900 ring-1 ring-indigo-200/80",
        className,
      )}
    >
      {label}
    </span>
  );
}
