"use client";

import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  value?: string;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
  leading?: ReactNode;
  /** Компактніший рядок для вузької лівої колонки. */
  compact?: boolean;
};

export function FilterRow({ label, value, onClick, className, disabled, leading, compact }: Props) {
  const filled = Boolean(value?.trim());

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex w-full items-center justify-between border border-border bg-white text-left transition-colors",
        "hover:border-emerald/30 focus:outline-none focus:border-emerald/50 focus:ring-2 focus:ring-emerald/10",
        compact
          ? "gap-2 rounded-lg px-3 py-2.5"
          : "gap-3 rounded-xl px-4 py-3.5",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    >
      <span className={cn("flex min-w-0 flex-1 items-center", compact ? "gap-2" : "gap-2.5")}>
        {leading}
        <span
          className={cn(
            "truncate",
            compact ? "text-[13px]" : "text-[15px]",
            filled ? "font-medium text-ink" : "text-muted",
          )}
        >
          {filled ? value : label}
        </span>
      </span>
      <svg width="8" height="14" viewBox="0 0 8 14" fill="none" className="shrink-0 text-muted/70" aria-hidden>
        <path d="M1 1l6 6-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}
