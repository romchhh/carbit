"use client";

import { useRouter } from "next/navigation";
import { IconCheck, IconTelegram } from "@/components/icons";
import { cn } from "@/lib/utils";

type Props = {
  connected: boolean;
  connectedMonitorId?: string | null;
  saving?: boolean;
  limitReached?: boolean;
  onSave: () => void;
  className?: string;
  /** Компактніший варіант у мобільному FAB. */
  compact?: boolean;
};

/** Кнопка підключення моніторингу — помітний primary CTA. */
export function DesktopSearchMonitorFab({
  connected,
  connectedMonitorId,
  saving,
  limitReached,
  onSave,
  className,
  compact = false,
}: Props) {
  const router = useRouter();

  const handleClick = () => {
    if (saving || limitReached) return;
    if (connected && connectedMonitorId) {
      router.push(`/app/monitors/${connectedMonitorId}`);
      return;
    }
    onSave();
  };

  if (connected) {
    return (
      <button
        type="button"
        data-tour="save-search"
        onClick={handleClick}
        className={cn(
          "flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-emerald/45 bg-emerald/10 px-4 font-bold text-emerald-dark transition-colors hover:bg-emerald/15",
          compact ? "py-2.5 text-[12px]" : "py-3.5 text-[14px]",
          className,
        )}
      >
        <IconCheck size={compact ? 16 : 20} strokeWidth={2.5} className="text-emerald" />
        Моніторинг підключено
      </button>
    );
  }

  return (
    <button
      type="button"
      data-tour="save-search"
      onClick={handleClick}
      disabled={saving || limitReached}
      className={cn(
        "group relative flex w-full flex-col items-center justify-center gap-0.5 overflow-hidden rounded-2xl px-4 font-bold text-white transition-all",
        "bg-gradient-to-br from-emerald via-emerald to-emerald-dark shadow-[0_10px_28px_-8px_rgba(16,185,129,0.65)]",
        "hover:brightness-105 active:scale-[0.99]",
        "disabled:cursor-not-allowed disabled:opacity-65 disabled:shadow-none",
        compact ? "py-2.5" : "py-3.5",
        className,
      )}
    >
      <span
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(255,255,255,0.28),transparent_55%)]"
        aria-hidden
      />
      <span className={cn("relative inline-flex items-center gap-2", compact ? "text-[12px]" : "text-[15px]")}>
        <IconTelegram size={compact ? 16 : 20} className="text-white" />
        {saving ? "Підключаємо…" : "Підключити моніторинг"}
      </span>
      {!compact && (
        <span className="relative text-[11px] font-medium text-white/90">
          Нові авто — одразу в Telegram
        </span>
      )}
    </button>
  );
}
