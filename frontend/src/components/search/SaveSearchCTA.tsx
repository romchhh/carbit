"use client";

import Link from "next/link";
import { IconTelegram } from "@/components/icons";
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
        "rounded-2xl border border-[#229ED9]/25 bg-[#E8F4FD]/50 px-4 py-3.5 sm:px-5",
        className,
      )}
      data-tour="save-search"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-[14px] font-bold text-ink">Моніторинг у Telegram</p>
          <p className="mt-0.5 text-[12px] leading-snug text-muted">
            Нові лоти за вашими фільтрами — одразу в чат.
            {!telegramConnected && (
              <>
                {" "}
                <Link
                  href="/app/account"
                  className="font-semibold text-[#229ED9] underline-offset-2 hover:underline"
                >
                  Підключіть Telegram
                </Link>
              </>
            )}
          </p>
        </div>

        <button
          type="button"
          onClick={onSave}
          disabled={saving || limitReached}
          className={cn(
            "inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-[#229ED9] px-5 py-2.5 text-[13px] font-bold text-white transition-colors hover:bg-[#1a8bc4]",
            "disabled:cursor-not-allowed disabled:opacity-60",
          )}
        >
          <IconTelegram size={16} />
          {saving ? "Підключаємо…" : "Підключити моніторинг"}
        </button>
      </div>

      {successMessage && (
        <p className="mt-2 text-[12px] font-medium text-emerald-dark">{successMessage}</p>
      )}
      {limitReached && (
        <p className="mt-2 text-[12px] text-amber-800">
          Ліміт моніторингів вичерпано.{" "}
          <Link href="/app/billing" className="font-semibold underline-offset-2 hover:underline">
            Оформити підписку
          </Link>
        </p>
      )}
      {errorMessage && !limitReached && (
        <p className="mt-2 text-[12px] font-medium text-red-600">{errorMessage}</p>
      )}
    </div>
  );
}
