"use client";

import { useEffect, useState, type ReactNode, type RefObject } from "react";
import { IconFilter, IconTelegram } from "@/components/icons";
import { MobileSearchFiltersModal } from "@/components/search/MobileSearchFiltersModal";
import { cn } from "@/lib/utils";

type MonitorProps = {
  onClick: () => void;
  saving?: boolean;
  disabled?: boolean;
  connected?: boolean;
  label?: string;
};

type Props = {
  targetRef: RefObject<HTMLElement | null>;
  className?: string;
  renderFilters: (close: () => void) => ReactNode;
  /** Завжди показувати панель (не ховати, коли фільтри у viewport). */
  pinned?: boolean;
  /** Показувати панель під час перегляду результатів пошуку. */
  visibleWhileSearching?: boolean;
  /** Фільтри на mobile лише в модалці — орієнтуємось на скрол, не на aside. */
  filtersMobileHidden?: boolean;
  monitor?: MonitorProps;
  /** Відступ знизу для fixed-панелі. */
  bottomInset?: "cabinet" | "public";
};

export function MobileSearchFiltersFab({
  targetRef,
  className,
  renderFilters,
  pinned = false,
  visibleWhileSearching = false,
  filtersMobileHidden = false,
  monitor,
  bottomInset = "cabinet",
}: Props) {
  const [filtersVisible, setFiltersVisible] = useState(true);
  const [scrolledDown, setScrolledDown] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (pinned || filtersMobileHidden) return;
    const target = targetRef.current;
    if (!target) return;

    const root = target.closest(".app-mobile-scroll") as HTMLElement | null;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setFiltersVisible(entry.isIntersecting);
      },
      {
        root,
        threshold: 0,
        rootMargin: "-64px 0px 0px 0px",
      },
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [filtersMobileHidden, pinned, targetRef]);

  useEffect(() => {
    if (!filtersMobileHidden) {
      setScrolledDown(false);
      return;
    }
    const root = targetRef.current?.closest(".app-mobile-scroll") as HTMLElement | null;
    if (!root) return;

    const onScroll = () => {
      setScrolledDown(root.scrollTop > 72);
    };
    onScroll();
    root.addEventListener("scroll", onScroll, { passive: true });
    return () => root.removeEventListener("scroll", onScroll);
  }, [filtersMobileHidden, targetRef]);

  const showBar =
    pinned ||
    visibleWhileSearching ||
    (filtersMobileHidden ? scrolledDown : !filtersVisible);

  const bottomClass =
    bottomInset === "public"
      ? "bottom-[max(1rem,env(safe-area-inset-bottom,0px))]"
      : "bottom-[calc(var(--mobile-nav-height,72px)+var(--compare-bar-inset,12px))]";

  return (
    <>
      <div
        className={cn(
          "fixed inset-x-3 z-[46] flex gap-2 lg:hidden",
          bottomClass,
          "transition-all duration-300",
          showBar
            ? "pointer-events-auto translate-y-0 opacity-100"
            : "pointer-events-none translate-y-3 opacity-0",
          className,
        )}
      >
        <button
          type="button"
          aria-label="Відкрити фільтри"
          onClick={() => setModalOpen(true)}
          className={cn(
            "inline-flex min-h-[48px] flex-1 items-center justify-center gap-2 rounded-2xl bg-emerald px-4 py-3",
            "text-[13px] font-bold text-white shadow-[0_8px_24px_-6px_rgba(16,185,129,0.55)]",
            "transition-all active:scale-[0.98]",
          )}
        >
          <IconFilter size={18} />
          Фільтри
        </button>

        {monitor ? (
          <button
            type="button"
            data-tour="save-search"
            onClick={monitor.onClick}
            disabled={monitor.saving || monitor.disabled}
            className={cn(
              "inline-flex min-h-[48px] flex-[1.15] items-center justify-center gap-2 rounded-2xl px-3 py-3",
              "text-[12px] font-bold text-white shadow-[0_8px_24px_-6px_rgba(251,146,60,0.5)]",
              "bg-gradient-to-br from-orange-300 via-orange-400 to-orange-500",
              "transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-65",
            )}
          >
            <IconTelegram size={17} className="shrink-0 text-white" />
            <span className="leading-tight">
              {monitor.saving
                ? "Підключаємо…"
                : monitor.connected
                  ? "Підключено"
                  : monitor.label ?? "Моніторинг"}
            </span>
          </button>
        ) : null}
      </div>

      <MobileSearchFiltersModal open={modalOpen} onClose={() => setModalOpen(false)}>
        {modalOpen ? renderFilters(() => setModalOpen(false)) : null}
      </MobileSearchFiltersModal>
    </>
  );
}
