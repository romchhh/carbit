"use client";

import Link from "next/link";
import { IconTelegram, IconZap, IconArrowRight } from "@/components/icons";
import { cn } from "@/lib/utils";

type Props = {
  onSave: () => void;
  saving?: boolean;
  successMessage?: string | null;
  errorMessage?: string | null;
  limitReached?: boolean;
  telegramConnected?: boolean;
  className?: string;
};

export function SaveSearchCTA({
  onSave,
  saving,
  successMessage,
  errorMessage,
  limitReached,
  telegramConnected,
  className,
}: Props) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-[#229ED9]/25 bg-gradient-to-br from-[#E8F4FD] via-white to-emerald-light/40 p-4 sm:p-5",
        className,
      )}
    >
      <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-[#229ED9]/10" />
      <div className="pointer-events-none absolute -bottom-8 -left-4 h-20 w-20 rounded-full bg-emerald/10" />

      <div className="relative flex gap-3 sm:gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#229ED9] text-white shadow-md shadow-[#229ED9]/25 sm:h-12 sm:w-12">
          <IconTelegram size={22} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <IconZap size={14} className="shrink-0 text-emerald-dark" />
            <p className="text-[13px] font-bold leading-snug text-ink sm:text-[14px]">
              Збережіть моніторинг — нові авто приходитимуть у Telegram
            </p>
          </div>
          <p className="mt-1.5 text-[12px] leading-relaxed text-muted sm:text-[13px]">
            Carbit відстежує AUTO.RIA та OLX за вашими фільтрами 24/7 і надсилає сповіщення, коли з&apos;являється нова пропозиція — без ручного перегляду каталогу.
          </p>

          {!telegramConnected && (
            <p className="mt-2 text-[11px] leading-snug text-[#229ED9]">
              Спочатку{" "}
              <Link href="/app/account" className="font-semibold underline-offset-2 hover:underline">
                підключіть Telegram
              </Link>
              {" "}в акаунті — тоді сповіщення приходитимуть миттєво.
            </p>
          )}

          {successMessage && (
            <p className="mt-2 rounded-lg bg-emerald/10 px-3 py-2 text-[12px] font-medium text-emerald-dark">
              {successMessage}
            </p>
          )}

          {limitReached && (
            <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-3 sm:px-4">
              <p className="text-[13px] font-semibold text-ink">
                Ліміт збережених пошуків вичерпано
              </p>
              <p className="mt-1 text-[12px] leading-relaxed text-muted">
                На безкоштовному тарифі доступний лише один активний пошук. Оформіть підписку, щоб зберігати більше запитів і отримувати сповіщення в Telegram.
              </p>
              <Link
                href="/app/billing"
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-full bg-ink py-3 text-[13px] font-bold text-white transition-colors hover:bg-ink-2 sm:w-auto sm:px-5"
              >
                Оформити підписку
                <IconArrowRight size={14} />
              </Link>
            </div>
          )}

          {errorMessage && !limitReached && (
            <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-[12px] font-medium text-red-600">
              {errorMessage}
            </p>
          )}

          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            className={cn(
              "mt-3 flex w-full items-center justify-center gap-2.5 rounded-full py-3.5 text-[14px] font-bold transition-all sm:mt-4 sm:w-auto sm:px-6",
              "bg-[#229ED9] text-white shadow-lg shadow-[#229ED9]/25 hover:bg-[#1a8bc4] active:scale-[0.99]",
              "disabled:cursor-not-allowed disabled:opacity-60",
            )}
          >
            <IconTelegram size={18} />
            {saving ? "Зберігаємо..." : "Зберегти пошук"}
          </button>
        </div>
      </div>
    </div>
  );
}
