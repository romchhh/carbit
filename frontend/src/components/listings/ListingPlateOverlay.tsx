"use client";

import { cn } from "@/lib/utils";

type Props = {
  plate: string;
  className?: string;
};

/** Держномер поверх фото картки (стилізація UA-таблички). */
export function ListingPlateOverlay({ plate, className }: Props) {
  const value = plate.trim();
  if (!value) return null;

  return (
    <div
      className={cn(
        "pointer-events-none inline-flex items-stretch overflow-hidden rounded-md border-2 border-ink/90 shadow-[0_2px_10px_rgba(0,0,0,0.35)]",
        className,
      )}
      aria-label={`Держномер ${value}`}
    >
      <span className="flex items-center bg-[#005bbb] px-1.5 text-[9px] font-bold uppercase tracking-wide text-white">
        UA
      </span>
      <span className="bg-[#f4ebc8] px-2 py-0.5 font-mono text-[11px] font-bold tracking-[0.14em] text-ink sm:text-[12px]">
        {value}
      </span>
    </div>
  );
}
