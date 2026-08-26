"use client";

import { useEffect, useState, type ReactNode, type RefObject } from "react";
import { useRouter } from "next/navigation";
import { IconCheck, IconFilter, IconTelegram } from "@/components/icons";
import { MobileSearchFiltersModal } from "@/components/search/MobileSearchFiltersModal";
import { cn } from "@/lib/utils";

type MonitorProps = {
  visible: boolean;
  connected: boolean;
  connectedMonitorId?: string | null;
  saving?: boolean;
  limitReached?: boolean;
  onSave: () => void;
};

type Props = {
  targetRef: RefObject<HTMLElement | null>;
  className?: string;
  /** Якщо задано — «Фільтри» відкривають модалку замість скролу. */
  renderFilters?: (close: () => void) => ReactNode;
  /** Завжди показувати панель (не ховати, коли фільтри у viewport). */
  pinned?: boolean;
  monitor?: MonitorProps;
  /** Відступ знизу для fixed-панелі. */
  bottomInset?: "cabinet" | "public";
};

export function MobileSearchFiltersFab({
  targetRef,
  className,
  renderFilters,
  pinned = false,
  monitor,
  bottomInset = "cabinet",
}: Props) {
  const router = useRouter();
  const [filtersVisible, setFiltersVisible] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (pinned || renderFilters) return;
    const target = targetRef.current;
    if (!target) return;

    const root = target.closest(".app-mobile-scroll") as HTMLElement | null;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setFiltersVisible(!entry.isIntersecting);
      },
      {
        root,
        threshold: 0,
        rootMargin: "-64px 0px 0px 0px",
      },
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [pinned, renderFilters, targetRef]);

  const scrollToFilters = () => {
    targetRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const openFilters = () => {
    if (renderFilters) {
      setModalOpen(true);
      return;
    }
    scrollToFilters();
  };

  const handleMonitorClick = () => {
    if (!monitor || monitor.saving || monitor.limitReached) return;
    if (monitor.connected && monitor.connectedMonitorId) {
      router.push(`/app/monitors/${monitor.connectedMonitorId}`);
      return;
    }
    monitor.onSave();
  };

  const showMonitor = Boolean(monitor?.visible);
  const showFiltersButton = pinned || renderFilters || filtersVisible;
  const showCluster = showFiltersButton || showMonitor;

  const bottomClass =
    bottomInset === "public"
      ? "bottom-[max(1rem,env(safe-area-inset-bottom,0px))]"
      : "bottom-[calc(var(--mobile-nav-height,72px)+var(--compare-bar-inset,12px))]";

  return (
    <>
      <div
        className={cn(
          "fixed right-3 z-[46] flex flex-row-reverse items-center gap-2 lg:hidden",
          bottomClass,
          "transition-all duration-300",
          showCluster
            ? "pointer-events-auto translate-y-0 opacity-100"
            : "pointer-events-none translate-y-3 opacity-0",
          className,
        )}
      >
        {showFiltersButton ? (
          <button
            type="button"
            aria-label="Відкрити фільтри"
            onClick={openFilters}
            className={cn(
              "inline-flex items-center gap-2 rounded-full bg-emerald px-4 py-3",
              "text-[13px] font-bold text-white shadow-[0_8px_24px_-6px_rgba(16,185,129,0.55)]",
              "transition-all active:scale-[0.97]",
            )}
          >
            <IconFilter size={18} />
            Фільтри
          </button>
        ) : null}

        {showMonitor && monitor ? (
          <button
            type="button"
            data-tour="save-search"
            onClick={handleMonitorClick}
            disabled={monitor.saving || monitor.limitReached}
            className={cn(
              "inline-flex items-center gap-2 rounded-full border-2 bg-white px-3.5 py-2.5",
              "text-[12px] font-bold shadow-[0_8px_24px_-6px_rgba(16,185,129,0.35)]",
              "transition-all active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60",
              monitor.connected
                ? "border-emerald/50 text-emerald-dark"
                : "border-emerald text-ink",
            )}
          >
            {monitor.connected ? (
              <>
                <IconCheck size={16} strokeWidth={2.5} className="text-emerald" />
                Підключено
              </>
            ) : (
              <>
                <IconTelegram size={16} className="text-emerald" />
                {monitor.saving ? "Підключаємо…" : "Моніторинг"}
              </>
            )}
          </button>
        ) : null}
      </div>

      {renderFilters ? (
        <MobileSearchFiltersModal open={modalOpen} onClose={() => setModalOpen(false)}>
          {modalOpen ? renderFilters(() => setModalOpen(false)) : null}
        </MobileSearchFiltersModal>
      ) : null}
    </>
  );
}
