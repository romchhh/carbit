"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { UserAvatar } from "@/components/ui/UserAvatar";
import { useAuth } from "@/contexts/AuthProvider";
import { useDashboardBadges } from "@/components/layout/DashboardSidebar";
import { primaryNav, secondaryNav } from "@/lib/dashboard-nav";
import { cn, PLAN_LABELS } from "@/lib/utils";
import { IconZap } from "@/components/icons";

const PLAN_CHIP: Record<string, string> = {
  free: "Free",
  lite: "Старт",
  standard: "Про",
  pro: "Бізнес",
};

export function DashboardTopNav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const badges = useDashboardBadges();
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

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  const planId = user.plan || "free";
  const planChip = PLAN_CHIP[planId] ?? PLAN_LABELS[planId] ?? planId;
  const isFree = planId === "free";

  return (
    <header className="mb-4 hidden shrink-0 lg:block">
      <div className="rounded-[22px] border border-border/50 bg-white px-4 py-3 shadow-island">
        <div className="flex items-center gap-4">
          <Link href="/app/dashboard" className="flex shrink-0 items-center pr-1">
            <CarbitLogo variant="full" height={28} />
          </Link>

          <nav
            className="flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            aria-label="Навігація кабінету"
          >
            {primaryNav.map(({ href, icon: Icon, label, badgeKey, badgeAccent, tourId }) => {
              const active = isActive(href);
              const badge = badgeKey ? badges[badgeKey] : 0;
              return (
                <Link
                  key={href}
                  href={href}
                  data-tour={tourId}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-2 text-[12px] font-semibold transition-colors xl:px-3.5 xl:text-[13px]",
                    active
                      ? "border-emerald/35 bg-emerald/12 text-emerald-dark shadow-sm"
                      : "border-border/70 bg-white text-ink/80 hover:border-emerald/25 hover:bg-surface hover:text-ink",
                  )}
                >
                  <Icon size={15} className={active ? "text-emerald-dark" : "text-ink/70"} />
                  <span className="whitespace-nowrap">{label}</span>
                  {badge > 0 && (
                    <span
                      className={cn(
                        "min-w-[18px] rounded-md px-1 py-0.5 text-center text-[10px] font-bold leading-none",
                        badgeAccent ? "bg-ink text-white" : "bg-emerald text-white",
                      )}
                    >
                      {badge > 99 ? "99+" : badge}
                    </span>
                  )}
                </Link>
              );
            })}

            {secondaryNav.map(({ href, icon: Icon, label, tourId }) => {
              const active = isActive(href);
              return (
                <Link
                  key={href}
                  href={href}
                  data-tour={tourId}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-2 text-[12px] font-medium transition-colors xl:px-3",
                    active
                      ? "border-border bg-surface font-semibold text-ink shadow-sm"
                      : "border-border/60 bg-white text-muted hover:border-border hover:bg-surface hover:text-ink",
                  )}
                >
                  <Icon size={14} />
                  <span className="hidden whitespace-nowrap xl:inline">{label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="flex shrink-0 items-center gap-2 pl-2">
            <Link
              href="/app/billing"
              className={cn(
                "inline-flex h-8 items-center gap-1 rounded-full px-2.5 text-[11px] font-bold ring-1 transition-colors",
                isFree
                  ? "bg-surface text-ink ring-border hover:bg-white"
                  : "bg-emerald/12 text-emerald-dark ring-emerald/25 hover:bg-emerald/18",
              )}
            >
              <IconZap size={12} />
              {planChip}
            </Link>

            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen(v => !v)}
                className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full ring-2 ring-border/60 transition-colors hover:ring-emerald/30"
                aria-expanded={menuOpen}
                aria-label="Меню акаунта"
              >
                <UserAvatar
                  name={user.name}
                  avatarUrl={user.avatar_url}
                  className="h-9 w-9 text-[12px] font-bold"
                />
              </button>

              {menuOpen && (
                <div className="absolute right-0 top-full z-50 mt-2 w-52 overflow-hidden rounded-2xl border border-border/70 bg-white py-1 shadow-card">
                  <div className="border-b border-border/60 px-3 py-2.5">
                    <div className="truncate text-[13px] font-semibold text-ink">{user.name}</div>
                    <div className="truncate text-[11px] text-muted">{user.email}</div>
                  </div>
                  <Link
                    href="/app/account"
                    className="block px-3 py-2.5 text-[13px] text-ink hover:bg-surface"
                    onClick={() => setMenuOpen(false)}
                  >
                    Акаунт
                  </Link>
                  <Link
                    href="/app/billing"
                    className="block px-3 py-2.5 text-[13px] text-ink hover:bg-surface"
                    onClick={() => setMenuOpen(false)}
                  >
                    Підписка
                  </Link>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      logout();
                    }}
                    className="block w-full px-3 py-2.5 text-left text-[13px] text-red-600 hover:bg-red-50"
                  >
                    Вийти
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
