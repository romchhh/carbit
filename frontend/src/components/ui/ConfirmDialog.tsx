"use client";

import { useEffect, useId } from "react";
import { Button } from "@/components/ui/Button";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";

type Props = {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Лише кнопка OK (замість alert). */
  alertOnly?: boolean;
  variant?: "danger" | "primary" | "emerald";
  loading?: boolean;
  onClose: () => void;
  onConfirm?: () => void;
};

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Підтвердити",
  cancelLabel = "Скасувати",
  alertOnly = false,
  variant = "danger",
  loading = false,
  onClose,
  onConfirm,
}: Props) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    lockBodyScroll();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      unlockBodyScroll();
      document.removeEventListener("keydown", onKey);
    };
  }, [open, loading, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-ink/40 p-4 sm:p-6"
      role="presentation"
      onClick={() => {
        if (!loading) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-md overflow-hidden rounded-2xl border border-border bg-white shadow-xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="px-5 py-5">
          <h2 id={titleId} className="text-[16px] font-bold text-ink">
            {title}
          </h2>
          {description && (
            <p className="mt-2 text-[13px] leading-relaxed text-muted">{description}</p>
          )}
        </div>

        <div className="flex flex-col-reverse gap-2 border-t border-border/70 bg-surface/40 px-5 py-4 sm:flex-row sm:justify-end">
          {!alertOnly && (
            <Button variant="secondary" size="md" disabled={loading} onClick={onClose}>
              {cancelLabel}
            </Button>
          )}
          <Button
            variant={variant}
            size="md"
            loading={loading}
            onClick={() => {
              if (alertOnly) {
                onClose();
                return;
              }
              onConfirm?.();
            }}
          >
            {alertOnly ? confirmLabel || "Зрозуміло" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
