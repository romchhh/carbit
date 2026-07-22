"use client";

import { Minus, Plus } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

type FaqItem = {
  q: string;
  a: string;
};

type Props = {
  items: readonly FaqItem[];
  /** Індекс відкритого пункту за замовчуванням; null — усі закриті */
  defaultOpen?: number | null;
  className?: string;
};

export function FaqAccordion({ items, defaultOpen = null, className }: Props) {
  const [openIndex, setOpenIndex] = useState<number | null>(defaultOpen);

  return (
    <ul className={cn("mx-auto flex max-w-[760px] list-none flex-col gap-3 sm:gap-3.5", className)}>
      {items.map(({ q, a }, index) => {
        const open = openIndex === index;
        const panelId = `faq-panel-${index}`;
        const buttonId = `faq-trigger-${index}`;

        return (
          <li key={q}>
            <div
              className={cn(
                "overflow-hidden rounded-2xl border bg-white transition-[border-color,box-shadow,transform] duration-300 ease-out",
                open
                  ? "border-emerald/35 shadow-[0_12px_40px_-16px_rgba(16,185,129,0.35)] ring-1 ring-emerald/10"
                  : "border-border/60 shadow-[0_1px_2px_rgba(10,12,14,0.04)] hover:border-border hover:shadow-[0_8px_24px_-12px_rgba(10,12,14,0.08)]",
              )}
            >
              <button
                id={buttonId}
                type="button"
                aria-expanded={open}
                aria-controls={panelId}
                onClick={() => setOpenIndex(open ? null : index)}
                className={cn(
                  "flex w-full items-start gap-4 px-5 py-4 text-left sm:px-6 sm:py-[1.125rem]",
                  "group transition-colors duration-200",
                  open ? "bg-surface/40" : "hover:bg-surface/30",
                )}
              >
                <span
                  className={cn(
                    "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border transition-all duration-300",
                    open
                      ? "border-emerald bg-emerald text-white"
                      : "border-border/80 bg-surface text-muted group-hover:border-emerald/30",
                  )}
                  aria-hidden
                >
                  {open ? <Minus className="h-4 w-4" strokeWidth={2.5} /> : <Plus className="h-4 w-4" strokeWidth={2.5} />}
                </span>
                <span className="min-w-0 flex-1 pt-0.5">
                  <span
                    className={cn(
                      "block text-[15px] font-semibold leading-snug tracking-[-0.01em] sm:text-[16px]",
                      open ? "text-ink" : "text-ink/90",
                    )}
                  >
                    {q}
                  </span>
                </span>
              </button>

              <div
                id={panelId}
                role="region"
                aria-labelledby={buttonId}
                className={cn(
                  "grid transition-[grid-template-rows] duration-300 ease-out",
                  open ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
                )}
              >
                <div className="overflow-hidden">
                  <div className="border-t border-border/50 px-5 pb-5 pt-4 sm:px-6 sm:pb-6 sm:pt-4">
                    <p className="pl-12 text-[14px] leading-[1.65] text-muted sm:text-[15px]">{a}</p>
                  </div>
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
