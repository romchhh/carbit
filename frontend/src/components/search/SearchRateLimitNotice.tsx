"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { IconClock } from "@/components/icons";
import { cn } from "@/lib/utils";

type Props = {
  message?: string | null;
  retryAfterSeconds?: number | null;
  className?: string;
};

function formatRetryLabel(seconds: number, nowMs: number): { relative: string; absolute: string } {
  const safe = Math.max(0, Math.floor(seconds));
  const at = new Date(nowMs + safe * 1000);
  const absolute = at.toLocaleTimeString("uk-UA", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Kyiv",
  });

  if (safe < 60) {
    return { relative: "менш ніж за хвилину", absolute };
  }
  const minutes = Math.ceil(safe / 60);
  if (minutes < 60) {
    return {
      relative: minutes === 1 ? "через 1 хв" : `через ${minutes} хв`,
      absolute,
    };
  }
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (rest === 0) {
    return {
      relative: hours === 1 ? "через 1 год" : `через ${hours} год`,
      absolute,
    };
  }
  return {
    relative: `через ${hours} год ${rest} хв`,
    absolute,
  };
}

export function SearchRateLimitNotice({
  message,
  retryAfterSeconds,
  className,
}: Props) {
  const [remaining, setRemaining] = useState(
    () => Math.max(0, Math.floor(retryAfterSeconds ?? 0)),
  );
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    setRemaining(Math.max(0, Math.floor(retryAfterSeconds ?? 0)));
    setNowMs(Date.now());
  }, [retryAfterSeconds]);

  useEffect(() => {
    if (remaining <= 0) return;
    const id = window.setInterval(() => {
      setRemaining(prev => Math.max(0, prev - 1));
      setNowMs(Date.now());
    }, 1000);
    return () => window.clearInterval(id);
  }, [remaining > 0]);

  const labels = useMemo(
    () => (remaining > 0 ? formatRetryLabel(remaining, nowMs) : null),
    [remaining, nowMs],
  );

  return (
    <div
      role="status"
      className={cn(
        "flex gap-3 rounded-2xl border border-amber-300/80 bg-amber-50 px-3.5 py-3.5 text-[13px] leading-relaxed shadow-[0_1px_0_rgba(245,158,11,0.12)] sm:px-4",
        className,
      )}
    >
      <span
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500 text-white shadow-sm"
        aria-hidden
      >
        <span className="text-[18px] leading-none">⏳</span>
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-bold text-amber-950">
          {message?.trim() || "Ліміт пошуків на годину вичерпано."}
        </p>
        {labels ? (
          <p className="mt-1.5 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-amber-900/80">
            <IconClock size={14} className="shrink-0 text-amber-700" />
            <span>
              Спробувати знову можна{" "}
              <strong className="font-semibold text-amber-950">{labels.relative}</strong>
              <span className="text-amber-800/70"> · близько {labels.absolute}</span>
            </span>
          </p>
        ) : (
          <p className="mt-1.5 text-amber-900/80">
            Ліміт уже скинувся — можна шукати знову.
          </p>
        )}
        <p className="mt-2.5 text-amber-900/75">
          На платному тарифі ліміти вищі.{" "}
          <Link
            href="/app/billing"
            className="font-bold text-amber-950 underline decoration-amber-400/70 underline-offset-2 transition-colors hover:text-amber-800"
          >
            Оформити підписку →
          </Link>
        </p>
      </div>
    </div>
  );
}

export function isSearchRateLimitMessage(message: string | null | undefined): boolean {
  return Boolean(message && /ліміт пошуків/i.test(message));
}
