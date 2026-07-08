"use client";

import { useEffect, useRef, useState } from "react";
import { SEARCH_PAGE_SIZE } from "@/lib/search-preview";
import { cn } from "@/lib/utils";

type Props = {
  active: boolean;
  label?: string;
  hint?: string | null;
  className?: string;
  compact?: boolean;
};

export function SearchProgressBar({
  active,
  label = "Шукаємо авто…",
  hint,
  className,
  compact = false,
}: Props) {
  const [visible, setVisible] = useState(false);
  const [progress, setProgress] = useState(0);
  const wasActive = useRef(false);

  useEffect(() => {
    if (active) {
      wasActive.current = true;
      setVisible(true);
      setProgress(10);

      const interval = window.setInterval(() => {
        setProgress(current => {
          if (current >= 92) return current;
          const increment = current < 30 ? 9 : current < 60 ? 5 : current < 85 ? 2 : 0.6;
          return Math.min(current + increment, 92);
        });
      }, 320);

      return () => window.clearInterval(interval);
    }

    if (!wasActive.current) return;

    setProgress(100);
    const hideTimer = window.setTimeout(() => {
      setVisible(false);
      setProgress(0);
      wasActive.current = false;
    }, 450);

    return () => window.clearTimeout(hideTimer);
  }, [active]);

  if (!visible) return null;

  const defaultHint =
    hint === undefined
      ? `Покажемо перші ${SEARCH_PAGE_SIZE} авто — решту можна підвантажити кнопкою «Показати ще»`
      : hint;

  return (
    <div
      className={cn(
        "overflow-hidden rounded-2xl border border-emerald/20 bg-white",
        compact ? "px-3 py-2.5" : "p-4",
        className,
      )}
      role="status"
      aria-live="polite"
      aria-valuenow={Math.round(progress)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className={cn("flex items-center justify-between gap-3", !compact && "mb-3")}>
        <p className={cn("font-medium text-ink", compact ? "text-[12px]" : "text-[13px]")}>{label}</p>
        <span className="text-[11px] tabular-nums text-muted">{Math.round(progress)}%</span>
      </div>
      <div className={cn("overflow-hidden rounded-full bg-surface", compact ? "h-1.5" : "h-2")}>
        <div
          className="h-full rounded-full bg-gradient-to-r from-emerald to-emerald-dark transition-[width] duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      {!compact && defaultHint && (
        <p className="mt-2.5 text-[11px] leading-relaxed text-muted">{defaultHint}</p>
      )}
    </div>
  );
}
