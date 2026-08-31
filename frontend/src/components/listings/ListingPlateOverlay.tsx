"use client";

import { cn } from "@/lib/utils";
import { ListingPlateBadge } from "@/components/listings/ListingPlateBadge";

type Props = {
  plate: string;
  className?: string;
};

/** Держномер поверх фото картки. */
export function ListingPlateOverlay({ plate, className }: Props) {
  return (
    <ListingPlateBadge
      plate={plate}
      size="sm"
      elevated
      className={cn("pointer-events-none", className)}
    />
  );
}
