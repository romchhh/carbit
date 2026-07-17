"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

type Props = {
  src: string;
  alt?: string;
  size?: number;
  className?: string;
};

export function BrandIcon({ src, alt = "", size = 20, className }: Props) {
  const [hidden, setHidden] = useState(false);

  if (hidden) return null;

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      width={size}
      height={size}
      loading="lazy"
      decoding="async"
      onError={() => setHidden(true)}
      className={cn("shrink-0 object-contain", className)}
      style={{ width: size, height: size }}
    />
  );
}
