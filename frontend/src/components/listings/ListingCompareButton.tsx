"use client";

import { IconCompare } from "@/components/icons";
import { cn } from "@/lib/utils";

type Props = {
  active: boolean;
  disabled?: boolean;
  onToggle: () => void;
  className?: string;
  size?: "sm" | "md";
  variant?: "default" | "overlay";
};

export function ListingCompareButton({
  active,
  disabled,
  onToggle,
  className,
  size = "sm",
  variant = "default",
}: Props) {
  return (
    <button
      type="button"
      aria-label={active ? "Прибрати з порівняння" : "Додати до порівняння"}
      aria-pressed={active}
      disabled={disabled}
      onClick={e => {
        e.preventDefault();
        e.stopPropagation();
        onToggle();
      }}
      className={cn(
        "inline-flex items-center justify-center rounded-full border-0 p-0 transition-all",
        variant === "overlay"
          ? cn(
              "shadow-[0_2px_10px_rgba(0,0,0,0.28)] backdrop-blur-[3px]",
              size === "sm" ? "h-9 w-9" : "h-10 w-10",
              active
                ? "bg-emerald text-white ring-2 ring-emerald/50"
                : "bg-black/55 text-white hover:bg-black/70",
              disabled && !active && "opacity-40 cursor-not-allowed",
            )
          : cn(
              "bg-transparent shadow-none",
              active ? "text-emerald" : "text-muted/75 hover:text-emerald-dark",
              size === "sm" ? "h-8 w-8" : "h-9 w-9",
              disabled && !active && "opacity-40",
            ),
        disabled && active && "opacity-60",
        className,
      )}
    >
      <IconCompare
        size={variant === "overlay" ? (size === "sm" ? 17 : 19) : size === "sm" ? 15 : 17}
        className={cn(
          variant === "overlay" && !active && "drop-shadow-[0_1px_2px_rgba(0,0,0,0.35)]",
        )}
      />
    </button>
  );
}
