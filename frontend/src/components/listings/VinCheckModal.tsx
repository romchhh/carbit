"use client";

import { useEffect } from "react";
import { IconX } from "@/components/icons";
import { VinCheckResultView } from "@/components/listings/VinCheckResultView";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";
import type { VinCheckResult } from "@/types/api";

type Props = {
  open: boolean;
  onClose: () => void;
  result: VinCheckResult | null;
  loading?: boolean;
  error?: string | null;
};

export function VinCheckModal({ open, onClose, result, loading, error }: Props) {
  useEffect(() => {
    if (!open) return;
    lockBodyScroll();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      unlockBodyScroll();
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] flex items-end justify-center sm:items-center">
      <button
        type="button"
        aria-label="Закрити"
        className="absolute inset-0 bg-ink/45 backdrop-blur-[2px]"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Перевірка VIN"
        className="relative z-10 flex max-h-[88vh] w-full max-w-lg flex-col overflow-hidden rounded-t-3xl border border-border bg-white shadow-2xl sm:rounded-3xl"
      >
        <div className="flex items-center justify-between border-b border-border/70 px-4 py-3.5 sm:px-5">
          <h2 className="text-[15px] font-bold text-ink">Перевірка VIN · База ДАІ</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1.5 text-muted transition-colors hover:bg-surface hover:text-ink"
            aria-label="Закрити"
          >
            <IconX size={18} />
          </button>
        </div>
        <div className="overflow-y-auto px-4 py-4 sm:px-5 sm:py-5">
          {loading && <p className="text-[13px] text-muted">Запит до Бази ДАІ…</p>}
          {error && (
            <p role="alert" className="text-[13px] font-medium text-red-600">
              {error}
            </p>
          )}
          {result && !loading && <VinCheckResultView result={result} />}
        </div>
      </div>
    </div>
  );
}
