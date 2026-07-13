"use client";

import Link from "next/link";
import { IconArrowRight, IconBell, IconTelegram } from "@/components/icons";
import { cn } from "@/lib/utils";
import type { SearchFreshness } from "@/lib/search-preview";

type Props = {
  total: number;
  shown: number;
  freshness: SearchFreshness;
  onSave: () => void;
  saving?: boolean;
  telegramConnected?: boolean;
  className?: string;
};

export function SearchPreviewNotice({
  total,
  shown,
  freshness,
  onSave,
  saving,
  telegramConnected,
  className,
}: Props) {
  const remaining = Math.max(total - shown, 0);

  return (
    <div
      className={cn(
        "relative mt-5 overflow-hidden rounded-2xl border border-emerald/20 bg-gradient-to-br from-emerald-light/80 via-white to-[#E8F4FD]/60 p-5 sm:p-6",
        className,
      )}
    >
      <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-emerald/10" />
      <div className="pointer-events-none absolute -bottom-12 -left-8 h-28 w-28 rounded-full bg-[#229ED9]/10" />

      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald/15 text-emerald-dark">
              <IconBell size={18} />
            </span>
            <p className="text-[15px] font-bold leading-snug text-ink sm:text-[16px]">
              Нехай ринок шукає за вас?
            </p>
          </div>
          <p className="mt-2 max-w-[540px] text-[13px] leading-relaxed text-muted sm:text-[14px]">
            {freshness === "new"
              ? "Це свіжина за тиждень — як ранок на автобазарі. "
              : "Обійшли майданчики за вашими фільтрами. "}
            {remaining > 0 ? (
              <>
                Ще можна заглянути в наступний ряд — там ще{" "}
                <strong className="font-semibold text-ink">
                  {remaining.toLocaleString("uk-UA")}+
                </strong>
                .{" "}
              </>
            ) : null}
            Збережіть моніторинг — нові лоти самі постукають у Telegram.
          </p>
          {!telegramConnected && (
            <p className="mt-2 text-[12px] text-[#229ED9]">
              <Link href="/app/account" className="font-semibold underline-offset-2 hover:underline">
                Підключіть Telegram
              </Link>
              {" "}в акаунті, щоб отримувати сповіщення миттєво.
            </p>
          )}
        </div>

        <button
          type="button"
          onClick={onSave}
          disabled={saving}
          className={cn(
            "inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-[#229ED9] px-5 py-3.5 text-[14px] font-bold text-white shadow-lg shadow-[#229ED9]/20 transition-all hover:bg-[#1a8bc4] active:scale-[0.99]",
            "disabled:cursor-not-allowed disabled:opacity-60",
          )}
        >
          <IconTelegram size={18} />
          {saving ? "Зберігаємо..." : "Зберегти пошук"}
          <IconArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}
