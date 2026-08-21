"use client";

import Image from "next/image";
import Link from "next/link";
import { IconCompare, IconTrash, IconX } from "@/components/icons";
import { useListingCompare } from "@/hooks/useListingCompare";
import { cn } from "@/lib/utils";

function shortTitle(title: string, max = 22): string {
  const trimmed = title.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max)}…`;
}

export function CompareBar() {
  const { items, count, max, remove, clear } = useListingCompare();

  if (count === 0) return null;

  return (
    <div
      className={cn(
        "fixed z-[45] left-0 right-0 px-2 sm:px-4",
        "bottom-[calc(var(--mobile-nav-height,72px)+8px)] lg:bottom-6",
        "lg:left-3 lg:right-5 lg:max-w-none lg:mx-0 xl:left-4 xl:right-7",
      )}
    >
      <div className="rounded-2xl border border-emerald/30 bg-white/96 shadow-[0_10px_40px_-10px_rgba(10,12,14,0.28)] backdrop-blur-md">
        <div className="flex items-center gap-2 px-2.5 py-2 sm:gap-3 sm:px-4 sm:py-3">
          <div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-emerald/10 px-2 py-1 text-[11px] font-bold text-emerald-dark sm:hidden">
              <IconCompare size={14} />
              {count}/{max}
            </span>
            <span className="hidden shrink-0 items-center gap-1.5 text-[12px] font-bold text-emerald-dark sm:inline-flex">
              <IconCompare size={16} />
              Порівняння
            </span>
            {items.map(item => {
              const image = item.images?.[0];
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => remove(item.id)}
                  className="group flex max-w-[168px] shrink-0 items-center gap-2 rounded-xl border border-border/70 bg-surface/80 p-1 pr-2 text-left transition active:scale-[0.98] hover:border-red-200 hover:bg-red-50/80 sm:max-w-[200px] sm:rounded-full sm:px-2.5 sm:py-1.5"
                  title="Прибрати з порівняння"
                >
                  <span className="relative h-9 w-9 shrink-0 overflow-hidden rounded-lg bg-white sm:h-7 sm:w-7 sm:rounded-full">
                    {image ? (
                      <Image
                        src={image}
                        alt=""
                        fill
                        className="object-cover"
                        sizes="36px"
                        unoptimized
                      />
                    ) : (
                      <span className="flex h-full items-center justify-center text-[9px] text-muted">
                        —
                      </span>
                    )}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[11px] font-semibold text-ink sm:max-w-[140px]">
                    {shortTitle(item.title)}
                  </span>
                  <IconX size={13} className="shrink-0 text-muted group-hover:text-red-500" />
                </button>
              );
            })}
          </div>

          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            <span className="hidden text-[11px] font-medium text-muted tabular-nums sm:inline">
              {count}/{max}
            </span>
            <button
              type="button"
              onClick={clear}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted hover:bg-surface hover:text-ink sm:h-auto sm:w-auto sm:px-2 sm:py-1.5 sm:text-[11px] sm:font-semibold"
              aria-label="Очистити порівняння"
              title="Очистити"
            >
              <IconTrash size={16} className="sm:hidden" />
              <span className="hidden sm:inline">Очистити</span>
            </button>
            <Link
              href="/app/compare"
              className={cn(
                "inline-flex min-h-10 items-center rounded-xl px-3.5 text-[12px] font-bold transition sm:min-h-0 sm:py-2 sm:text-[13px]",
                count >= 2
                  ? "bg-emerald text-white shadow-sm hover:bg-emerald-dark active:scale-[0.98]"
                  : "pointer-events-none bg-surface text-muted",
              )}
              aria-disabled={count < 2}
              title={count < 2 ? "Оберіть ще мінімум одне авто" : "Відкрити порівняння"}
            >
              Порівняти
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
