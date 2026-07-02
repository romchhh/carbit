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
        "inline-flex items-center justify-center rounded-full border-0 bg-transparent p-0 shadow-none transition-colors",
        active
          ? "text-emerald"
          : variant === "overlay"
            ? "text-white drop-shadow-[0_1px_4px_rgba(0,0,0,0.45)] hover:text-emerald"
            : "text-muted/75 hover:text-emerald-dark",
        loading && "opacity-60",
        size === "sm" ? "h-8 w-8" : "h-9 w-9",
        className,
      )}
    >
      <IconHeart
        size={size === "sm" ? 15 : 17}
        className={cn("transition-colors", active && "fill-current")}
      />
    </button>
  );
}
