"use client";

import { IconHeart } from "@/components/icons";
import { cn } from "@/lib/utils";

type Props = {
  active: boolean;
  loading?: boolean;
  onToggle: () => void;
  className?: string;
  size?: "sm" | "md";
  variant?: "default" | "overlay";
};

export function ListingFavoriteButton({
  active,
  loading,
  onToggle,
  className,
  size = "sm",
  variant = "default",
}: Props) {
  return (
    <button
      type="button"
      aria-label={active ? "Прибрати з обраного" : "Додати в обране"}
      aria-pressed={active}
      disabled={loading}
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
                ? "bg-white text-emerald ring-2 ring-emerald/40"
                : "bg-black/55 text-white hover:bg-black/70",
            )
          : cn(
              "bg-transparent shadow-none",
              active
                ? "text-emerald"
                : "text-muted/75 hover:text-emerald-dark",
              size === "sm" ? "h-8 w-8" : "h-9 w-9",
            ),
        loading && "opacity-60",
        className,
      )}
    >
      <IconHeart
        size={variant === "overlay" ? (size === "sm" ? 17 : 19) : size === "sm" ? 15 : 17}
        className={cn(
          "transition-colors",
          active && "fill-current",
          variant === "overlay" && !active && "drop-shadow-[0_1px_2px_rgba(0,0,0,0.35)]",
        )}
      />
    </button>
  );
}
