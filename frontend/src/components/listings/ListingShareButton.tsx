"use client";

import { useState } from "react";
import { IconShare } from "@/components/icons";
import {
  buildListingShareUrl,
  listingShareTitle,
  shareOrCopyUrl,
} from "@/lib/listing-share";
import { cn } from "@/lib/utils";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing;
  className?: string;
  size?: "sm" | "md";
  variant?: "default" | "overlay";
  /** Короткий текст-підказка після копіювання (опційно зовні). */
  onResult?: (message: string) => void;
};

export function ListingShareButton({
  listing,
  className,
  size = "sm",
  variant = "default",
  onResult,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const handleShare = async () => {
    if (busy) return;
    setBusy(true);
    const url = buildListingShareUrl(listing.id);
    const result = await shareOrCopyUrl({
      url,
      title: listingShareTitle(listing),
    });
    setBusy(false);
    if (result === "copied" || result === "shared") {
      const message =
        result === "shared" ? "Посилання надіслано" : "Посилання на картку скопійовано";
      onResult?.(message);
      setDone(true);
      window.setTimeout(() => setDone(false), 2000);
    } else {
      onResult?.(url);
    }
  };

  return (
    <button
      type="button"
      aria-label="Поділитися посиланням на авто"
      title={done ? "Скопійовано" : "Поділитися"}
      disabled={busy}
      onClick={e => {
        e.preventDefault();
        e.stopPropagation();
        void handleShare();
      }}
      className={cn(
        "inline-flex items-center justify-center rounded-full border-0 p-0 transition-all",
        variant === "overlay"
          ? cn(
              "shadow-[0_2px_10px_rgba(0,0,0,0.28)] backdrop-blur-[3px]",
              size === "sm" ? "h-9 w-9" : "h-10 w-10",
              done
                ? "bg-emerald text-white ring-2 ring-emerald/50"
                : "bg-black/55 text-white hover:bg-black/70",
            )
          : cn(
              "bg-transparent shadow-none",
              done ? "text-emerald" : "text-muted/75 hover:text-emerald-dark",
              size === "sm" ? "h-8 w-8" : "h-9 w-9",
            ),
        busy && "opacity-60",
        className,
      )}
    >
      <IconShare
        size={variant === "overlay" ? (size === "sm" ? 17 : 19) : size === "sm" ? 15 : 17}
        className={cn(
          variant === "overlay" && !done && "drop-shadow-[0_1px_2px_rgba(0,0,0,0.35)]",
        )}
      />
    </button>
  );
}
