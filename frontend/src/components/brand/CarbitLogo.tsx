import Image from "next/image";
import { cn } from "@/lib/utils";

import { APP_ICON_SRC, FULL_LOGO_SRC, FULL_LOGO_WHITE_SRC } from "@/lib/brand-assets";

type CarbitLogoProps = {
  variant?: "icon" | "full";
  height?: number;
  light?: boolean;
  className?: string;
  priority?: boolean;
};

export function CarbitLogo({
  variant = "full",
  height = 32,
  light = false,
  className,
  priority = false,
}: CarbitLogoProps) {
  const src =
    variant === "icon"
      ? APP_ICON_SRC
      : light
        ? FULL_LOGO_WHITE_SRC
        : FULL_LOGO_SRC;

  return (
    <Image
      src={src}
      alt="Carbit"
      width={variant === "icon" ? height : Math.round(height * 3.4)}
      height={height}
      priority={priority}
      className={cn(
        "w-auto shrink-0 object-contain",
        variant === "icon" ? "aspect-square object-center" : "",
        className,
      )}
      style={{ height }}
    />
  );
}
