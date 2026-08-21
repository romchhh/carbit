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
  /** Desktop-only fixed FAB (default). Mobile uses MobileSearchFiltersFab cluster. */
  className?: string;
};

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
        "fixed bottom-6 right-6 z-[46] hidden items-center gap-2.5 rounded-full border-2 px-5 py-3.5",
        "text-[14px] font-bold shadow-[0_12px_32px_-8px_rgba(10,12,14,0.35)] transition-all lg:inline-flex",
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
