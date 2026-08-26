"use client";

import { useEffect, useId, type ReactNode } from "react";
import { IconX } from "@/components/icons";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";
import { cn } from "@/lib/utils";

type Props = {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  className?: string;
};

export function MobileSearchFiltersModal({ open, onClose, children, className }: Props) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    lockBodyScroll();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      unlockBodyScroll();
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className={cn("fixed inset-0 z-[120] flex flex-col justify-end lg:hidden", className)}
      role="presentation"
    >
      <button
        type="button"
        aria-label="Закрити фільтри"
        className="absolute inset-0 bg-ink/45 backdrop-blur-[2px]"
        onClick={onClose}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative flex max-h-[min(94dvh,920px)] w-full flex-col overflow-hidden rounded-t-[1.5rem] border border-border/80 bg-surface shadow-[0_-20px_60px_-20px_rgba(10,12,14,0.35)]"
      >
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border/70 bg-white px-4 py-3.5">
          <div className="min-w-0">
            <h2 id={titleId} className="text-[17px] font-bold text-ink">
              Фільтри
            </h2>
            <p className="text-[12px] text-muted">Налаштуйте пошук і натисніть «Шукати»</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрити"
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border bg-white text-ink transition-colors hover:border-ink/20 hover:bg-surface"
          >
            <IconX size={18} />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-4 pb-[calc(env(safe-area-inset-bottom,0px)+1rem)]">
          {children}
        </div>
      </div>
    </div>
  );
}
