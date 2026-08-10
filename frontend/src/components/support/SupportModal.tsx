"use client";

import { useEffect } from "react";
import { IconTelegram, IconX } from "@/components/icons";
import { FaqAccordion } from "@/components/ui/FaqAccordion";
import { CARBIT_FAQ_ITEMS } from "@/lib/faq-items";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";
import { getTelegramSupportBotMention, getTelegramSupportBotUrl } from "@/lib/telegram";
import { cn } from "@/lib/utils";

type Props = {
  open: boolean;
  onClose: () => void;
};

export function SupportModal({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    lockBodyScroll();
    return () => unlockBodyScroll();
  }, [open]);

  if (!open) return null;

  const openBot = () => {
    window.open(getTelegramSupportBotUrl(), "_blank", "noopener,noreferrer");
  };

  return (
    <div
      className="fixed inset-0 z-[120] flex items-end justify-center p-4 sm:items-center sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="support-modal-title"
    >
      <button
        type="button"
        aria-label="Закрити"
        className="absolute inset-0 bg-ink/55 backdrop-blur-[6px]"
        onClick={onClose}
      />

      <div
        className={cn(
          "relative flex max-h-[min(90dvh,720px)] w-full max-w-[480px] flex-col overflow-hidden rounded-[28px] bg-white shadow-[0_24px_80px_-12px_rgba(0,0,0,0.35)]",
        )}
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-border/60 px-5 py-4 sm:px-6">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-emerald-dark">
              Підтримка
            </p>
            <h2
              id="support-modal-title"
              className="mt-1 text-[18px] font-bold tracking-tight text-ink sm:text-[20px]"
            >
              Часті питання
            </h2>
            <p className="mt-1 text-[13px] text-muted">
              Не знайшли відповідь? Напишіть боту — відповімо про тариф, оплату та сервіс.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-surface text-ink transition-colors hover:bg-white"
            aria-label="Закрити"
          >
            <IconX size={16} />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3 sm:px-4">
          <FaqAccordion items={CARBIT_FAQ_ITEMS} className="max-w-none gap-2" />
        </div>

        <div className="shrink-0 border-t border-border/60 bg-surface/40 px-5 py-4 sm:px-6">
          <button
            type="button"
            onClick={openBot}
            className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#229ED9] px-5 py-3 text-[14px] font-bold text-white transition hover:brightness-110"
          >
            <IconTelegram size={18} />
            Написати {getTelegramSupportBotMention()}
          </button>
          <p className="mt-2 text-center text-[11px] text-muted">
            Бот відповідає на питання про підписку, оплату та роботу сервісу
          </p>
        </div>
      </div>
    </div>
  );
}
