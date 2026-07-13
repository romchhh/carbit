"use client";

import { useEffect, useRef, useState } from "react";
import { SEARCH_HINTS, SEARCH_LABELS } from "@/lib/search-flavor";
import { cn } from "@/lib/utils";

type Props = {
  active: boolean;
  /** Якщо передано — фіксований заголовок; інакше крутимо креативні варіанти. */
  label?: string;
  hint?: string | null;
  className?: string;
  compact?: boolean;
};

export function SearchProgressBar({
  active,
  label,
  hint,
  className,
  compact = false,
}: Props) {
  const [visible, setVisible] = useState(false);
  const [progress, setProgress] = useState(0);
  const [flavorIndex, setFlavorIndex] = useState(0);
  const wasActive = useRef(false);

  useEffect(() => {
    if (active) {
      wasActive.current = true;
      setVisible(true);
      setProgress(10);
      setFlavorIndex(Math.floor(Math.random() * SEARCH_LABELS.length));

      const progressInterval = window.setInterval(() => {
        setProgress(current => {
          if (current >= 92) return current;
          const increment = current < 30 ? 9 : current < 60 ? 5 : current < 85 ? 2 : 0.6;
          return Math.min(current + increment, 92);
        });
      }, 320);

      const flavorInterval = window.setInterval(() => {
        setFlavorIndex(current => (current + 1) % SEARCH_LABELS.length);
      }, 2800);

      return () => {
        window.clearInterval(progressInterval);
        window.clearInterval(flavorInterval);
      };
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

  const rotatingLabel = SEARCH_LABELS[flavorIndex % SEARCH_LABELS.length]!;
  const rotatingHint = SEARCH_HINTS[flavorIndex % SEARCH_HINTS.length]!;
  const displayLabel = label ?? rotatingLabel;
  const displayHint = hint === undefined ? rotatingHint : hint;

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
        <p
          key={displayLabel}
          className={cn(
            "font-medium text-ink transition-opacity duration-300",
            compact ? "text-[12px]" : "text-[13px]",
          )}
        >
          {displayLabel}
        </p>
        <span className="text-[11px] tabular-nums text-muted">{Math.round(progress)}%</span>
      </div>
      <div className={cn("overflow-hidden rounded-full bg-surface", compact ? "h-1.5" : "h-2")}>
        <div
          className="h-full rounded-full bg-gradient-to-r from-emerald to-emerald-dark transition-[width] duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      {!compact && displayHint && (
        <p
          key={displayHint}
          className="mt-2.5 text-[11px] leading-relaxed text-muted transition-opacity duration-300"
        >
          {displayHint}
        </p>
      )}
    </div>
  );
}
