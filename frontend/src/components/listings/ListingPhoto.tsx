"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { FULL_LOGO_SRC } from "@/lib/brand-assets";
import { cn } from "@/lib/utils";

type Props = {
  src?: string | null;
  alt: string;
  /** Показувати спінер замість лого, поки фото очікується. */
  pending?: boolean;
  className?: string;
  imageClassName?: string;
  sizes?: string;
  logoClassName?: string;
  pendingLabel?: string | null;
  priority?: boolean;
};

/** Фото оголошення: без фото / помилка завантаження → логотип Carbit. */
export function ListingPhoto({
  src,
  alt,
  pending = false,
  className,
  imageClassName,
  sizes = "300px",
  logoClassName,
  pendingLabel = "Завантаження фото…",
  priority = false,
}: Props) {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [src]);

  const showImage = Boolean(src) && !failed;

  if (showImage) {
    return (
      <div className={cn("relative h-full w-full overflow-hidden bg-surface", className)}>
        <Image
          src={src as string}
          alt={alt}
          fill
          className={cn("object-cover", imageClassName)}
          sizes={sizes}
          loading={priority ? undefined : "lazy"}
          priority={priority || undefined}
          decoding="async"
          unoptimized
          onError={() => setFailed(true)}
        />
      </div>
    );
  }

  if (pending) {
    return (
      <div
        className={cn(
          "flex h-full w-full flex-col items-center justify-center gap-2 bg-gradient-to-br from-surface to-border/40",
          className,
        )}
      >
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-muted/50" />
        {pendingLabel ? (
          <span className="text-[11px] text-muted/70">{pendingLabel}</span>
        ) : null}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex h-full w-full items-center justify-center bg-gradient-to-br from-surface via-white to-emerald/[0.06]",
        className,
      )}
      aria-label="Немає фото"
    >
      <Image
        src={FULL_LOGO_SRC}
        alt="Carbit"
        width={160}
        height={48}
        className={cn("h-8 w-auto opacity-70 sm:h-9", logoClassName)}
        unoptimized
      />
    </div>
  );
}
