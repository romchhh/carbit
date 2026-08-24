"use client";

import type { ReactNode, RefObject } from "react";
import { cn } from "@/lib/utils";

type Props = {
  filtersRef: RefObject<HTMLDivElement | null>;
  filters: ReactNode;
  results: ReactNode;
  footer?: ReactNode;
  className?: string;
};

/** Desktop: фільтри зліва (sticky), результати справа. Mobile: вертикальний stack. */
export function SearchDesktopSplit({ filtersRef, filters, results, footer, className }: Props) {
  return (
    <div
      className={cn(
        "lg:grid lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)] lg:items-start lg:gap-4 xl:grid-cols-[minmax(0,320px)_minmax(0,1fr)] xl:gap-5",
        className,
      )}
    >
      <aside
        ref={filtersRef}
        className="mb-5 scroll-mt-4 sm:mb-6 lg:sticky lg:top-3 lg:mb-0 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto lg:overscroll-contain"
      >
        {filters}
      </aside>

      <div className="min-w-0">
        {results}
        {footer}
      </div>
    </div>
  );
}
