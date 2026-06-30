"use client";

import { useEffect, useState } from "react";
import { IconHeart } from "@/components/icons";
import { cn } from "@/lib/utils";

type Props = {
  active: boolean;
  loading?: boolean;
  onToggle: () => void;
  className?: string;
  size?: "sm" | "md";
};

export function ListingFavoriteButton({
  active,
  loading,
  onToggle,
  className,
  size = "sm",
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
        "inline-flex items-center justify-center rounded-full border transition-all",
        "bg-white/95 shadow-sm backdrop-blur-sm",
        active
          ? "border-red-200 text-red-500 hover:bg-red-50"
          : "border-border/80 text-muted hover:border-emerald/40 hover:text-emerald-dark",
        loading && "opacity-60",
        size === "sm" ? "h-8 w-8" : "h-9 w-9",
        className,
      )}
    >
      <IconHeart size={size === "sm" ? 15 : 17} className={active ? "fill-current" : undefined} />
    </button>
  );
}
