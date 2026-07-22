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
    <section
      className={cn(
        "rounded-2xl border px-3 py-2.5 transition-colors sm:px-3.5",
        open ? "border-border/80 bg-white" : "border-border/50 bg-surface/25",
      )}
    >
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
      {open ? <div className="mt-3 space-y-3.5 pb-1">{children}</div> : null}
    </section>
  );
}
