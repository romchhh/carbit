"use client";

import type { ReactNode, RefObject } from "react";
import { cn } from "@/lib/utils";

type Props = {
  filtersRef: RefObject<HTMLDivElement | null>;
  filters: ReactNode;
  results: ReactNode;
  /** Sticky під фільтрами на desktop (напр. «Підключити моніторинг»). */
  filtersFooter?: ReactNode;
  footer?: ReactNode;
  className?: string;
};

/** Desktop: фільтри зліва (sticky), результати справа. Mobile: вертикальний stack. */
export function SearchDesktopSplit({
  filtersRef,
  filters,
  filtersFooter,
  results,
  footer,
  className,
}: Props) {
  const hasFooter = Boolean(filtersFooter);

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
          "mb-5 scroll-mt-4 sm:mb-6 lg:sticky lg:top-3 lg:mb-0",
          hasFooter
            ? // Кнопка моніторингу завжди внизу колонки; фільтри скроляться окремо.
              "lg:flex lg:h-[calc(100dvh-7rem)] lg:max-h-[calc(100dvh-7rem)] lg:flex-col lg:overflow-hidden"
            : "lg:max-h-[calc(100dvh-7rem)] lg:overflow-y-auto lg:overscroll-contain",
        )}
      >
        <div
          className={cn(
            hasFooter && "min-h-0 flex-1 overflow-y-auto overscroll-contain pb-1",
          )}
        >
          {filters}
        </div>
        {hasFooter ? (
          <div className="relative z-20 hidden shrink-0 border-t border-border/60 bg-surface pt-3 shadow-[0_-8px_20px_-12px_rgba(10,12,14,0.18)] lg:block">
            {filtersFooter}
          </div>
        ) : null}
      </aside>

      <div className="min-w-0">
        {results}
        {footer}
      </div>
    </div>
  );
}
