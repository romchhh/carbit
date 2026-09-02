"use client";

import { cn } from "@/lib/utils";

type Props = {
  /** Компактний оверлей на фото картки. */
  variant?: "overlay" | "pill" | "label";
  className?: string;
};

/** Позначка «був у ДТП» для карток і сторінки оголошення. */
export function AccidentBadge({ variant = "pill", className }: Props) {
  const label = "Був у ДТП";

  if (variant === "overlay") {
    return (
      <span
        className={cn(
          "rounded-full bg-amber-600 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-white shadow-sm",
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
          "inline-flex rounded-full bg-amber-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-amber-800 ring-1 ring-amber-200/80",
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
        "rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-800 ring-1 ring-amber-200/80",
        className,
      )}
    >
      {label}
    </span>
  );
}
