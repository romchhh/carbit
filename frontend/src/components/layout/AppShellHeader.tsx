"use client";

import Link from "next/link";
import { useRef, useState, useEffect } from "react";
import { PLAN_LABELS, cn } from "@/lib/utils";
import { formatKyivDate } from "@/lib/datetime";
import { UserAvatar } from "@/components/ui/UserAvatar";
import { useAuth } from "@/contexts/AuthProvider";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { IconZap } from "@/components/icons";

type Props = {
  className?: string;
};

const PLAN_CHIP: Record<string, string> = {
  free: "Free",
  lite: "Старт",
  standard: "Про",
  pro: "Бізнес",
};

export function AppShellHeader({ className }: Props) {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [planOpen, setPlanOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const planRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node;
      if (menuRef.current && !menuRef.current.contains(target)) {
        setMenuOpen(false);
      }
      if (planRef.current && !planRef.current.contains(target)) {
        setPlanOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("touchstart", onClickOutside);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("touchstart", onClickOutside);
    };
  }, []);

  if (!user) return null;

  const planId = user.plan || "free";
  const isFree = planId === "free";
  const planChip = PLAN_CHIP[planId] ?? PLAN_LABELS[planId] ?? planId;
  const planFull = PLAN_LABELS[planId] ?? planId;
  const expiresAt = user.plan_expires_at || (user.is_trial_active ? user.trial_ends_at : null);

  return (
    <div
      className={cn(
        "pointer-events-none fixed inset-x-0 top-[var(--safe-top)] z-30 overflow-visible px-2 pt-2 lg:hidden",
        className,
      )}
    >
      <header
        className={cn(
          "glass-liquid glass-liquid-host pointer-events-auto flex items-center justify-between rounded-[24px] px-4 py-4",
        )}
      >
        <Link href="/app/dashboard" className="flex items-center">
          <CarbitLogo variant="full" height={34} />
        </Link>

        <div className="flex items-center gap-2">
          <div className="relative shrink-0" ref={planRef}>
            <button
              type="button"
              onClick={() => {
                setPlanOpen(v => !v);
                setMenuOpen(false);
              }}
              className={cn(
                "inline-flex h-9 items-center gap-1.5 rounded-full px-2.5 text-[12px] font-bold ring-1 transition-colors",
                isFree
                  ? "bg-white/70 text-ink ring-black/10 hover:bg-white/90"
                  : "bg-emerald/15 text-emerald-dark ring-emerald/30 hover:bg-emerald/25",
              )}
              aria-expanded={planOpen}
              aria-label={`Тариф ${planChip}`}
            >
              <IconZap size={13} className={isFree ? "text-ink/70" : "text-emerald-dark"} />
              <span>{planChip}</span>
            </button>

            {planOpen && (
              <div className="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-2xl border border-border/70 bg-white p-3 shadow-card">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                  Підписка
                </div>
                <div className="mt-1 text-[15px] font-bold text-ink">{planFull}</div>

                {isFree ? (
                  <>
                    {user.is_trial_active && user.trial_ends_at ? (
                      <p className="mt-1.5 text-[12px] leading-snug text-muted">
                        Пробний період до {formatKyivDate(user.trial_ends_at)}
                      </p>
                    ) : (
                      <p className="mt-1.5 text-[12px] leading-snug text-muted">
                        Без активної підписки
                      </p>
                    )}
                    <Link
                      href="/app/billing"
                      onClick={() => setPlanOpen(false)}
                      className="mt-3 flex w-full items-center justify-center rounded-full bg-emerald px-4 py-2.5 text-[13px] font-bold text-white transition-colors hover:bg-emerald-dark"
                    >
                      Оформити
                    </Link>
                  </>
                ) : (
                  <>
                    <p className="mt-1.5 text-[12px] leading-snug text-muted">
                      {expiresAt
                        ? `Діє до ${formatKyivDate(expiresAt)}`
                        : "Активна підписка"}
                    </p>
                    <Link
                      href="/app/billing"
                      onClick={() => setPlanOpen(false)}
                      className="mt-3 flex w-full items-center justify-center rounded-full border border-border bg-surface px-4 py-2.5 text-[13px] font-semibold text-ink transition-colors hover:bg-white"
                    >
                      Керувати підпискою
                    </Link>
                  </>
                )}
              </div>
            )}
          </div>

          <div className="relative shrink-0" ref={menuRef}>
            <button
              type="button"
              onClick={() => {
                setMenuOpen(v => !v);
                setPlanOpen(false);
              }}
              className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full ring-2 ring-white/70"
            >
              <UserAvatar
                name={user.name}
                avatarUrl={user.avatar_url}
                className="h-10 w-10 text-[13px] font-bold"
              />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-2xl border border-border/70 bg-white py-1 shadow-card">
                <div className="border-b border-border/60 px-3 py-2.5">
                  <div className="truncate text-[13px] font-semibold text-ink">{user.name}</div>
                  <div className="truncate text-[11px] text-muted">{user.email}</div>
                </div>
                <Link
                  href="/app/account"
                  data-tour="nav-account"
                  className="block px-3 py-2.5 text-[13px] text-ink transition-colors hover:bg-surface"
                  onClick={() => setMenuOpen(false)}
                >
                  Акаунт
                </Link>
                <Link
                  href="/app/search"
                  className="block px-3 py-2.5 text-[13px] text-ink transition-colors hover:bg-surface"
                  onClick={() => setMenuOpen(false)}
                >
                  Пошук
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    logout();
                  }}
                  className="block w-full px-3 py-2.5 text-left text-[13px] text-red-600 transition-colors hover:bg-red-50"
                >
                  Вийти
                </button>
              </div>
            )}
          </div>
        </div>
      </header>
    </div>
  );
}
