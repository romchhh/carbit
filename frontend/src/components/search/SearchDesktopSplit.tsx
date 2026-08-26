"use client";

import type { ReactNode, RefObject } from "react";
import { cn } from "@/lib/utils";

type Props = {
  filtersRef: RefObject<HTMLElement | null>;
  filters: ReactNode;
  results: ReactNode;
  /** Над результатами пошуку (напр. «Останні пошуки»). */
  resultsHeader?: ReactNode;
  footer?: ReactNode;
  className?: string;
  /** На mobile фільтри лише в модалці (aside ховається до lg). */
  filtersMobileHidden?: boolean;
};

/** Desktop: фільтри зліва (sticky), результати справа. Mobile: вертикальний stack. */
export function SearchDesktopSplit({
  filtersRef,
  filters,
  results,
  resultsHeader,
  footer,
  className,
  filtersMobileHidden = false,
}: Props) {
  return (
    <div
      className={cn(
        "lg:grid lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)] lg:items-start lg:gap-4 xl:grid-cols-[minmax(0,320px)_minmax(0,1fr)] xl:gap-5",
        className,
      )}
    >
      <aside
        ref={filtersRef}
        className={cn(
          "scroll-mt-4 lg:sticky lg:top-3 lg:mb-0 lg:self-start",
          filtersMobileHidden ? "hidden lg:block" : "mb-5 sm:mb-6 lg:mb-0",
        )}
      >
        {filters}
      </aside>

      <div className="min-w-0">
        {resultsHeader ? <div className="mb-4 sm:mb-5">{resultsHeader}</div> : null}
        {results}
        {footer}
      </div>
    </div>
  );
}
