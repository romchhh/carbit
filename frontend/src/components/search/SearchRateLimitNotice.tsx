"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
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
        "rounded-xl border border-border/80 bg-surface/70 px-3.5 py-3 text-[13px] leading-relaxed text-muted",
        className,
      )}
    >
      <p className="font-medium text-ink/80">
        {message?.trim() || "Ліміт пошуків на годину вичерпано."}
      </p>
      {labels ? (
        <p className="mt-1">
          Спробувати знову можна {labels.relative}
          <span className="text-ink/55"> · близько {labels.absolute}</span>
        </p>
      ) : (
        <p className="mt-1">Ліміт уже скинувся — можна шукати знову.</p>
      )}
      <p className="mt-2">
        На платному тарифі ліміти вищі.{" "}
        <Link
          href="/app/billing"
          className="font-semibold text-ink/70 underline decoration-border underline-offset-2 transition-colors hover:text-ink"
        >
          Оформити підписку
        </Link>
      </p>
    </div>
  );
}

export function isSearchRateLimitMessage(message: string | null | undefined): boolean {
  return Boolean(message && /ліміт пошуків/i.test(message));
}
