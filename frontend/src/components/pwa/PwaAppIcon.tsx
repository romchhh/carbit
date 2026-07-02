import Image from "next/image";

import { FULL_LOGO_SRC } from "@/lib/brand-assets";
import { cn } from "@/lib/utils";

type PwaAppIconProps = {
  size?: number;
  className?: string;
};

export function PwaAppIcon({ size = 56, className }: PwaAppIconProps) {
  const logoHeight = Math.max(Math.round(size * 0.34), 16);

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-[22%] bg-white ring-1 ring-black/[0.06]",
        className,
      )}
      style={{ width: size, height: size, padding: Math.round(size * 0.18) }}
      aria-hidden="true"
    >
      <Image
        src={FULL_LOGO_SRC}
        alt=""
        width={Math.round(logoHeight * 4.2)}
        height={logoHeight}
        className="h-auto w-full object-contain"
        style={{ maxHeight: logoHeight }}
      />
    </div>
  );
}
