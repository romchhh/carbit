"use client";

import Link from "next/link";
import { useRef, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { UserAvatar } from "@/components/ui/UserAvatar";
import { useAuth } from "@/contexts/AuthProvider";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { IconBell } from "@/components/icons";

type Props = {
  unreadNotifications?: number;
  className?: string;
};

export function AppShellHeader({ unreadNotifications = 0, className }: Props) {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent | TouchEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
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

  return (
    <div
      className={cn(
        "pointer-events-none fixed inset-x-0 top-[var(--safe-top)] z-30 overflow-visible px-3 pt-2 lg:hidden",
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

        <div className="flex items-center gap-2.5">
          <Link
            href="/app/notifications"
            className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/25 text-ink ring-1 ring-white/55 transition-colors hover:bg-white/40"
          >
            <IconBell size={18} />
            {unreadNotifications > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-ink px-1 text-[9px] font-bold text-white">
                {unreadNotifications > 9 ? "9+" : unreadNotifications}
              </span>
            )}
          </Link>

          <div className="relative shrink-0" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen(v => !v)}
              className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full ring-2 ring-white/70"
            >
              <UserAvatar
                name={user.name}
                avatarUrl={user.avatar_url}
                className="h-10 w-10 text-[13px] font-bold"
              />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-full z-50 mt-2 w-52 overflow-hidden rounded-2xl border border-border/70 bg-white py-1 shadow-card">
                <div className="border-b border-border/60 px-3 py-2.5">
                  <div className="truncate text-[13px] font-semibold text-ink">{user.name}</div>
                  <div className="truncate text-[11px] text-muted">{user.email}</div>
                </div>
                <Link href="/app/account" className="block px-3 py-2.5 text-[13px] text-ink transition-colors hover:bg-surface" onClick={() => setMenuOpen(false)}>
                  Акаунт
                </Link>
                <Link href="/app/billing" className="block px-3 py-2.5 text-[13px] text-ink transition-colors hover:bg-surface" onClick={() => setMenuOpen(false)}>
                  Підписка
                </Link>
                <button
                  type="button"
                  onClick={() => { setMenuOpen(false); logout(); }}
                  className={cn("block w-full px-3 py-2.5 text-left text-[13px] text-red-600 transition-colors hover:bg-red-50")}
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
