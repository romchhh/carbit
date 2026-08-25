"use client";

import { useRouter } from "next/navigation";
import { IconCheck, IconTelegram } from "@/components/icons";
import { cn } from "@/lib/utils";

type Props = {
  visible: boolean;
  connected: boolean;
  connectedMonitorId?: string | null;
  saving?: boolean;
  limitReached?: boolean;
  onSave: () => void;
  className?: string;
};

/** Desktop: кнопка моніторингу під колонкою фільтрів (не floating FAB). */
export function DesktopSearchMonitorFab({
  visible,
  connected,
  connectedMonitorId,
  saving,
  limitReached,
  onSave,
  className,
}: Props) {
  const router = useRouter();

  if (!visible) return null;

  const handleClick = () => {
    if (saving || limitReached) return;
    if (connected && connectedMonitorId) {
      router.push(`/app/monitors/${connectedMonitorId}`);
      return;
    }
    onSave();
  };

  return (
    <button
      type="button"
      data-tour="save-search"
      onClick={handleClick}
      disabled={saving || limitReached}
      className={cn(
        "flex w-full items-center justify-center gap-2 rounded-2xl border-2 px-4 py-3",
        "text-[13px] font-bold shadow-[0_8px_24px_-10px_rgba(10,12,14,0.28)] transition-all",
        "disabled:cursor-not-allowed disabled:opacity-60",
        connected
          ? "border-emerald/50 bg-white text-emerald-dark hover:bg-emerald/5"
          : "border-emerald bg-white text-ink hover:bg-emerald/5",
        className,
      )}
    >
      {connected ? (
        <>
          <IconCheck size={18} strokeWidth={2.5} className="text-emerald" />
          Моніторинг підключено
        </>
      ) : (
        <>
          <IconTelegram size={18} className="text-emerald" />
          {saving ? "Підключаємо…" : "Підключити моніторинг"}
        </>
      )}
    </button>
  );
}
