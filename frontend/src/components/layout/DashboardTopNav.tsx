"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { UserAvatar } from "@/components/ui/UserAvatar";
import { useAuth } from "@/contexts/AuthProvider";
import { useDashboardBadges } from "@/components/layout/DashboardSidebar";
import { primaryNav, secondaryNav } from "@/lib/dashboard-nav";
import { cn } from "@/lib/utils";
import { IconBell, IconCoin, IconHeart } from "@/components/icons";

const DESKTOP_NAV_HIDDEN = new Set([
  "/app/favorites",
  "/app/notifications",
  "/app/account",
  "/app/billing",
]);

function HeaderIconLink({
  href,
  label,
  active,
  badge,
  badgeAccent,
  children,
  tourId,
}: {
  href: string;
  label: string;
  active?: boolean;
  badge?: number;
  badgeAccent?: boolean;
  children: ReactNode;
  tourId?: string;
}) {
  return (
    <Link
      href={href}
      data-tour={tourId}
      aria-label={label}
      title={label}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative flex h-9 w-9 items-center justify-center rounded-full border transition-colors",
        active
          ? "border-emerald/35 bg-emerald/12 text-emerald-dark shadow-sm"
          : "border-border/70 bg-white text-ink/75 hover:border-emerald/25 hover:bg-surface hover:text-ink",
      )}
    >
      {children}
      {badge != null && badge > 0 && (
        <span
          className={cn(
            "absolute -right-0.5 -top-0.5 min-w-[16px] rounded-full px-1 py-0.5 text-center text-[9px] font-bold leading-none ring-2 ring-white",
            badgeAccent ? "bg-ink text-white" : "bg-emerald text-white",
          )}
        >
          {badge > 99 ? "99+" : badge}
        </span>
      )}
    </Link>
  );
}

export function DashboardTopNav() {
  const pathname = usePathname();
  const { user } = useAuth();
  const badges = useDashboardBadges();

  if (!user) return null;

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  const planId = user.plan || "free";
  const isFree = planId === "free";

  const mainNav = primaryNav.filter(item => !DESKTOP_NAV_HIDDEN.has(item.href));
  const utilityNav = secondaryNav.filter(item => !DESKTOP_NAV_HIDDEN.has(item.href));

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
            {mainNav.map(({ href, icon: Icon, label, badgeKey, badgeAccent, tourId }) => {
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

            {utilityNav.map(({ href, icon: Icon, label, tourId }) => {
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

          <div className="flex shrink-0 items-center gap-1.5 pl-2">
            <HeaderIconLink
              href="/app/notifications"
              label="Сповіщення"
              active={isActive("/app/notifications")}
              badge={badges.notifications}
              badgeAccent
              tourId="nav-notifications"
            >
              <IconBell size={17} />
            </HeaderIconLink>

            <HeaderIconLink
              href="/app/favorites"
              label="Обране"
              active={isActive("/app/favorites")}
              tourId="nav-favorites"
            >
              <IconHeart size={17} />
            </HeaderIconLink>

            <HeaderIconLink
              href="/app/billing"
              label="Підписка"
              active={isActive("/app/billing")}
              tourId="nav-billing"
            >
              <IconCoin
                size={17}
                className={isFree ? "text-ink/70" : "text-emerald-dark"}
              />
            </HeaderIconLink>

            <Link
              href="/app/account"
              data-tour="nav-account"
              aria-label="Акаунт"
              title="Акаунт"
              aria-current={isActive("/app/account") ? "page" : undefined}
              className={cn(
                "flex h-9 w-9 items-center justify-center overflow-hidden rounded-full ring-2 transition-colors",
                isActive("/app/account")
                  ? "ring-emerald/40"
                  : "ring-border/60 hover:ring-emerald/30",
              )}
            >
              <UserAvatar
                name={user.name}
                avatarUrl={user.avatar_url}
                className="h-9 w-9 text-[12px] font-bold"
              />
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
