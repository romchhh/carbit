"use client";

import Link from "next/link";
import { useRef, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { UserAvatar } from "@/components/ui/UserAvatar";
import { useAuth } from "@/contexts/AuthProvider";
import { LogoIcon } from "@/components/brand/LogoIcon";
import { IconBell } from "@/components/icons";

type Props = {
  unreadNotifications?: number;
};

export function AppShellHeader({ unreadNotifications = 0 }: Props) {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  if (!user) return null;

  return (
    <header className="mb-4 flex items-center justify-between lg:hidden">
      <Link href="/app/dashboard" className="flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink text-white shadow-sm">
          <LogoIcon size={18} light />
        </span>
        <span className="text-[17px] font-bold tracking-tight text-ink">Carbit</span>
      </Link>

      <div className="flex items-center gap-2">
        <Link
          href="/app/notifications"
          className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-border/70 bg-white text-muted transition-colors hover:text-ink"
        >
          <IconBell size={17} />
          {unreadNotifications > 0 && (
            <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-ink px-1 text-[9px] font-bold text-white">
              {unreadNotifications > 9 ? "9+" : unreadNotifications}
            </span>
          )}
        </Link>

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen(v => !v)}
            className="overflow-hidden"
          >
            <UserAvatar
              name={user.name}
              avatarUrl={user.avatar_url}
              rounded="xl"
              className="h-9 w-9 text-[12px] font-bold"
            />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full z-50 mt-2 w-48 overflow-hidden rounded-xl border border-border/70 bg-white py-1 shadow-card">
              <div className="border-b border-border/60 px-3 py-2.5">
                <div className="truncate text-[13px] font-semibold text-ink">{user.name}</div>
                <div className="truncate text-[11px] text-muted">{user.email}</div>
              </div>
              <Link href="/app/account" className="block px-3 py-2.5 text-[13px] text-ink hover:bg-surface" onClick={() => setMenuOpen(false)}>
                Акаунт
              </Link>
              <Link href="/app/billing" className="block px-3 py-2.5 text-[13px] text-ink hover:bg-surface" onClick={() => setMenuOpen(false)}>
                Підписка
              </Link>
              <button
                type="button"
                onClick={() => { setMenuOpen(false); logout(); }}
                className={cn("block w-full px-3 py-2.5 text-left text-[13px] text-red-600 hover:bg-red-50")}
              >
                Вийти
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
