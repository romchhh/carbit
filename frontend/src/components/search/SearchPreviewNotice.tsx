"use client";

import { useState } from "react";
import { IconTelegram } from "@/components/icons";
import { TelegramConnectPrompt } from "@/components/search/TelegramConnectPrompt";
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
  const [showTgPrompt, setShowTgPrompt] = useState(false);

  const handleSaveClick = () => {
    if (saving) return;
    if (!telegramConnected) {
      setShowTgPrompt(true);
      return;
    }
    onSave();
  };

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
          {remaining > 0 ? (
            <p className="text-[14px] leading-relaxed text-muted">
              {freshness === "new" ? "Свіжі за тиждень" : "За вашими фільтрами"}
              {" · "}ще{" "}
              <strong className="font-semibold text-ink">
                {remaining.toLocaleString("uk-UA")}+
              </strong>{" "}
              у наступних рядах
            </p>
          ) : (
            <p className="text-[14px] leading-relaxed text-muted">
              {freshness === "new"
                ? "Усі свіжі за тиждень уже на екрані"
                : "Усі знайдені авто вже на екрані"}
            </p>
          )}
        </div>

        <button
          type="button"
          onClick={handleSaveClick}
          disabled={saving}
          className={cn(
            "inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-[#229ED9] px-6 py-3.5 text-[15px] font-bold text-white shadow-lg shadow-[#229ED9]/20 transition-all hover:bg-[#1a8bc4] active:scale-[0.99] min-h-[48px] sm:min-h-[52px] sm:px-8 sm:py-4 sm:text-[16px] w-full sm:w-auto",
            "disabled:cursor-not-allowed disabled:opacity-60",
          )}
        >
          <IconTelegram size={18} />
          {saving ? "Зберігаємо..." : "Зберегти пошук"}
        </button>
      </div>

      <TelegramConnectPrompt
        open={showTgPrompt}
        onClose={() => setShowTgPrompt(false)}
        onContinueWithoutTelegram={onSave}
        onConnected={onSave}
      />
    </div>
  );
}
