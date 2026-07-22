"use client";

import { ChevronDown } from "lucide-react";
import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type Props = {
  title: string;
  defaultOpen?: boolean;
  badge?: number;
  children: ReactNode;
};

export function FilterAccordionSection({ title, defaultOpen = true, badge, children }: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="border-t border-border/60 pt-3 first:border-t-0 first:pt-0">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex w-full items-center justify-between gap-2 py-1 text-left"
      >
        <span className="flex items-center gap-2 text-[14px] font-bold text-ink">
          {title}
          {badge != null && badge > 0 ? (
            <span className="rounded-full bg-emerald/15 px-2 py-0.5 text-[11px] font-semibold text-emerald">
              {badge}
            </span>
          ) : null}
        </span>
        <ChevronDown
          className={cn("h-4 w-4 shrink-0 text-muted transition-transform", open && "rotate-180")}
        />
      </button>
      {open ? <div className="mt-2 space-y-2">{children}</div> : null}
    </section>
  );
}
