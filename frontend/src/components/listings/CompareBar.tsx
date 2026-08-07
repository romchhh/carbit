"use client";

import Link from "next/link";
import { IconCompare, IconX } from "@/components/icons";
import { useListingCompare } from "@/hooks/useListingCompare";
import { cn } from "@/lib/utils";

export function CompareBar() {
  const { items, count, max, remove, clear } = useListingCompare();

  if (count === 0) return null;

  return (
    <div
      className={cn(
        "fixed z-[45] left-0 right-0 px-2.5 sm:px-4",
        "bottom-[calc(var(--mobile-nav-height,72px)+6px)] lg:bottom-6",
        "lg:left-[calc(252px+1.5rem)] lg:right-6 lg:max-w-[980px] lg:mx-auto",
      )}
    >
      <div className="flex items-center gap-2 rounded-2xl border border-emerald/30 bg-white/95 px-3 py-2.5 shadow-[0_8px_32px_-8px_rgba(10,12,14,0.25)] backdrop-blur-md sm:gap-3 sm:px-4 sm:py-3">
        <div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto">
          <span className="hidden shrink-0 items-center gap-1.5 text-[12px] font-bold text-emerald-dark sm:inline-flex">
            <IconCompare size={16} />
            Порівняння
          </span>
          {items.map(item => (
            <button
              key={item.id}
              type="button"
              onClick={() => remove(item.id)}
              className="group flex max-w-[140px] shrink-0 items-center gap-1 rounded-full bg-surface px-2.5 py-1.5 text-left transition hover:bg-red-50"
              title="Прибрати з порівняння"
            >
              <span className="truncate text-[11px] font-semibold text-ink">{item.title}</span>
              <IconX size={12} className="shrink-0 text-muted group-hover:text-red-500" />
            </button>
          ))}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="text-[11px] font-medium text-muted tabular-nums">
            {count}/{max}
          </span>
          <button
            type="button"
            onClick={clear}
            className="hidden rounded-lg px-2 py-1.5 text-[11px] font-semibold text-muted hover:bg-surface hover:text-ink sm:block"
          >
            Очистити
          </button>
          <Link
            href="/app/compare"
            className={cn(
              "rounded-xl px-3.5 py-2 text-[12px] font-bold transition sm:text-[13px]",
              count >= 2
                ? "bg-emerald text-white shadow-sm hover:bg-emerald-dark"
                : "pointer-events-none bg-surface text-muted",
            )}
            aria-disabled={count < 2}
            title={count < 2 ? "Оберіть ще мінімум одне авто" : "Відкрити таблицю порівняння"}
          >
            Порівняти
          </Link>
        </div>
      </div>
    </div>
  );
}
