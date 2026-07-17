"use client";

import { useEffect, useId, useState } from "react";
import { IconTelegram, IconX } from "@/components/icons";
import { ApiError, telegram as telegramApi } from "@/lib/api";
import { useAuth } from "@/contexts/AuthProvider";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";

type Props = {
  open: boolean;
  onClose: () => void;
  /** Зберегти моніторинг без підключення Telegram */
  onContinueWithoutTelegram: () => void;
  /** Після успішного підключення Telegram — зберегти моніторинг */
  onConnected?: () => void;
};

export function TelegramConnectPrompt({
  open,
  onClose,
  onContinueWithoutTelegram,
  onConnected,
}: Props) {
  const titleId = useId();
  const { refreshUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [waiting, setWaiting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setError("");
    setWaiting(false);
    setLoading(false);
  }, [open]);

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

  useEffect(() => {
    if (!open || !waiting) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const status = await telegramApi.status();
        if (cancelled) return;
        if (status.connected) {
          await refreshUser();
          setWaiting(false);
          onConnected?.();
          onClose();
        }
      } catch {
        /* ignore poll errors */
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [open, waiting, refreshUser, onClose, onConnected]);

  if (!open) return null;

  const connectTelegram = async () => {
    setError("");
    setLoading(true);
    try {
      const link = await telegramApi.connectLink();
      window.open(link.bot_url, "_blank", "noopener,noreferrer");
      setWaiting(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося відкрити Telegram");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[90] flex items-end justify-center bg-ink/40 p-3 sm:items-center sm:p-6"
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
        <div className="flex items-start justify-between gap-3 border-b border-border/60 px-5 py-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#E8F4FD] text-[#229ED9]">
              <IconTelegram size={20} />
            </span>
            <div>
              <h2 id={titleId} className="text-[17px] font-bold tracking-tight text-ink">
                Бажаєте отримувати оголошення прямо в Telegram?
              </h2>
              <p className="mt-1.5 text-[13px] leading-relaxed text-muted">
                Підключіть акаунт — нові авто за вашими фільтрами приходитимуть у бот одразу,
                з фото та посиланням.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-ink disabled:opacity-50"
            aria-label="Закрити"
          >
            <IconX size={18} />
          </button>
        </div>

        <div className="space-y-3 px-5 py-4">
          {waiting && (
            <p className="rounded-lg border border-[#229ED9]/20 bg-[#E8F4FD]/60 px-3 py-2 text-[13px] text-[#1a6fa0]">
              Очікуємо підтвердження в Telegram… Після підключення можете зберегти моніторинг.
            </p>
          )}
          {error && (
            <p className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-[13px] text-red-600">
              {error}
            </p>
          )}

          <button
            type="button"
            disabled={loading}
            onClick={() => void connectTelegram()}
            className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#229ED9] px-4 py-3 text-[14px] font-bold text-white transition-colors hover:bg-[#1a8bc4] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            ) : (
              <IconTelegram size={18} />
            )}
            Підключити Telegram
          </button>

          <button
            type="button"
            disabled={loading}
            onClick={() => {
              onContinueWithoutTelegram();
              onClose();
            }}
            className="w-full rounded-full border border-border px-4 py-2.5 text-[13px] font-semibold text-ink transition-colors hover:bg-surface disabled:opacity-50"
          >
            Зберегти моніторинг без Telegram
          </button>
        </div>
      </div>
    </div>
  );
}
