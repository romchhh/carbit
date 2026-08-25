"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Props = {
  children: ReactNode;
  trailing?: ReactNode;
  className?: string;
};

export function FilterSubsectionLabel({ children, trailing, className }: Props) {
  return (
    <div className={cn("flex items-center justify-between gap-2", className)}>
      <div className="flex min-w-0 items-center gap-2">
        <span className="h-[1.125rem] w-[3px] shrink-0 rounded-full bg-emerald" aria-hidden />
        <span className="text-[13px] font-semibold tracking-[-0.01em] text-ink">{children}</span>
      </div>
      {trailing ? <div className="shrink-0">{trailing}</div> : null}
    </div>
  );
}
