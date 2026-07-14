"use client";

import { useEffect, useId, useState } from "react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export const CANCEL_RENEWAL_REASONS = [
  { id: "price", label: "Занадто дорого" },
  { id: "limits", label: "Мало моніторингів / обмеження тарифу" },
  { id: "results", label: "Погано знаходить потрібні авто" },
  { id: "usage", label: "Рідко користуюся" },
  { id: "tech", label: "Технічні проблеми / незручний інтерфейс" },
  { id: "other", label: "Інше" },
] as const;

export type CancelRenewalReasonId = (typeof CANCEL_RENEWAL_REASONS)[number]["id"];

type Props = {
  open: boolean;
  expiresAt?: string | null;
  loading?: boolean;
  error?: string;
  onClose: () => void;
  onConfirm: (payload: { reason: CancelRenewalReasonId; note: string }) => void;
};

export function CancelRenewalDialog({
  open,
  expiresAt,
  loading,
  error,
  onClose,
  onConfirm,
}: Props) {
  const titleId = useId();
  const [reason, setReason] = useState<CancelRenewalReasonId | "">("");
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!open) return;
    setReason("");
    setNote("");
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, loading, onClose]);

  if (!open) return null;

  const expiresLabel = expiresAt
    ? new Date(expiresAt).toLocaleDateString("uk-UA", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "кінця оплаченого періоду";

  const canSubmit = Boolean(reason) && (reason !== "other" || note.trim().length >= 3);

  return (
    <div
      className="fixed inset-0 z-[80] flex items-end justify-center bg-ink/40 p-3 sm:items-center sm:p-6"
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
        <div className="border-b border-border/70 px-5 py-4">
          <h2 id={titleId} className="text-[16px] font-bold text-ink">
            Скасувати автопродовження?
          </h2>
          <p className="mt-1.5 text-[13px] leading-relaxed text-muted">
            Доступ збережеться до {expiresLabel}. Далі щомісячні списання зупиняться.
          </p>
        </div>

        <div className="space-y-4 px-5 py-4">
          <div>
            <p className="text-[13px] font-semibold text-ink">Що саме не сподобалося?</p>
            <p className="mt-0.5 text-[12px] text-muted">Оберіть одну причину — це допоможе покращити сервіс.</p>
            <div className="mt-3 space-y-2">
              {CANCEL_RENEWAL_REASONS.map(item => (
                <label
                  key={item.id}
                  className={cn(
                    "flex cursor-pointer items-start gap-2.5 rounded-xl border px-3 py-2.5 transition",
                    reason === item.id
                      ? "border-emerald/50 bg-emerald-light/30"
                      : "border-border/80 hover:border-border",
                  )}
                >
                  <input
                    type="radio"
                    name="cancel-reason"
                    value={item.id}
                    checked={reason === item.id}
                    onChange={() => setReason(item.id)}
                    className="mt-0.5 accent-emerald"
                  />
                  <span className="text-[13px] text-ink">{item.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="cancel-note" className="text-[12px] font-semibold text-ink">
              {reason === "other" ? "Опишіть коротко" : "Деталі (необовʼязково)"}
            </label>
            <textarea
              id="cancel-note"
              value={note}
              onChange={e => setNote(e.target.value.slice(0, 500))}
              rows={3}
              placeholder="Наприклад: бракує фільтра по… / хотів би…"
              className="mt-1.5 w-full resize-none rounded-xl border border-border bg-surface px-3 py-2.5 text-[13px] text-ink placeholder:text-muted/70 focus:outline-none focus:ring-2 focus:ring-emerald/25"
            />
          </div>

          {error && (
            <p className="rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-[12px] text-red-600">
              {error}
            </p>
          )}
        </div>

        <div className="flex flex-col-reverse gap-2 border-t border-border/70 bg-surface/40 px-5 py-4 sm:flex-row sm:justify-end">
          <Button variant="secondary" size="md" disabled={loading} onClick={onClose}>
            Залишити автопродовження
          </Button>
          <Button
            variant="danger"
            size="md"
            loading={loading}
            disabled={!canSubmit}
            onClick={() => {
              if (!reason || !canSubmit) return;
              onConfirm({ reason, note: note.trim() });
            }}
          >
            Підтвердити скасування
          </Button>
        </div>
      </div>
    </div>
  );
}
