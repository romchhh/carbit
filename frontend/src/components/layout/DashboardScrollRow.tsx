"use client";

import { cn } from "@/lib/utils";

type Props = {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  tourId?: string;
  empty?: React.ReactNode;
  isEmpty?: boolean;
};

export function DashboardScrollRow({
  title,
  description,
  action,
  children,
  className,
  tourId,
  empty,
  isEmpty,
}: Props) {
  return (
    <section
      data-tour={tourId}
      className={cn(
        "rounded-2xl border border-border/70 bg-gradient-to-b from-white to-surface/20 p-4 shadow-sm sm:p-5",
        className,
      )}
    >
      <div className="mb-4 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-[16px] font-black tracking-tight text-ink sm:text-[17px]">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-[12px] leading-relaxed text-muted sm:text-[13px]">{description}</p>
          ) : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>

      {isEmpty && empty ? (
        empty
      ) : (
        <div
          className={cn(
            "flex gap-3 overflow-x-auto pb-1",
            "[scrollbar-width:thin] [&::-webkit-scrollbar]:h-1.5",
            "[&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-border",
            "[&::-webkit-scrollbar-track]:bg-transparent",
          )}
        >
          {children}
        </div>
      )}
    </section>
  );
}
