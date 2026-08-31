"use client";

import { cn } from "@/lib/utils";

type Size = "sm" | "md" | "lg";

type Props = {
  plate: string;
  size?: Size;
  className?: string;
  /** Тінь для накладання поверх фото */
  elevated?: boolean;
};

const SIZE_STYLES: Record<
  Size,
  {
    root: string;
    strip: string;
    flag: string;
    flagBlue: string;
    flagYellow: string;
    ua: string;
    text: string;
  }
> = {
  sm: {
    root: "rounded-[5px] border-[2px]",
    strip: "w-[17px] gap-0.5 px-0.5 py-1",
    flag: "w-[11px]",
    flagBlue: "h-[3px]",
    flagYellow: "h-[3px]",
    ua: "text-[7px] leading-none",
    text: "px-2 py-0.5 text-[11px] tracking-[0.1em]",
  },
  md: {
    root: "rounded-[7px] border-[2.5px]",
    strip: "w-[22px] gap-1 px-1 py-1.5",
    flag: "w-[14px]",
    flagBlue: "h-[4px]",
    flagYellow: "h-[4px]",
    ua: "text-[8px] leading-none",
    text: "px-3 py-1 text-[15px] tracking-[0.12em]",
  },
  lg: {
    root: "rounded-[8px] border-[3px]",
    strip: "w-[28px] gap-1 px-1 py-2",
    flag: "w-[18px]",
    flagBlue: "h-[5px]",
    flagYellow: "h-[5px]",
    ua: "text-[10px] leading-none",
    text: "px-4 py-1.5 text-[22px] tracking-[0.14em] sm:text-[24px]",
  },
};

/** UA-табличка: синя смуга з прапором + білий блок з номером. */
export function ListingPlateBadge({
  plate,
  size = "md",
  className,
  elevated = false,
}: Props) {
  const value = plate.trim();
  if (!value) return null;

  const styles = SIZE_STYLES[size];

  return (
    <div
      className={cn(
        "inline-flex items-stretch overflow-hidden border-black bg-white",
        styles.root,
        elevated && "shadow-[0_2px_10px_rgba(0,0,0,0.35)]",
        className,
      )}
      aria-label={`Держномер ${value}`}
    >
      <span
        className={cn(
          "flex shrink-0 flex-col items-center justify-center bg-[#0057b7]",
          styles.strip,
        )}
      >
        <span className={cn("flex w-full flex-col overflow-hidden rounded-[1px]", styles.flag)}>
          <span className={cn("w-full bg-[#0057b7]", styles.flagBlue)} />
          <span className={cn("w-full bg-[#ffd700]", styles.flagYellow)} />
        </span>
        <span className={cn("font-bold uppercase text-white", styles.ua)}>UA</span>
      </span>
      <span
        className={cn(
          "flex min-w-0 items-center justify-center bg-white font-bold uppercase text-black",
          styles.text,
        )}
      >
        {value}
      </span>
    </div>
  );
}
