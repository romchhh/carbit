"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { mobileNav, type NavBadgeKey } from "@/lib/dashboard-nav";

type Props = {
  badges: Record<NavBadgeKey, number>;
};

export function DashboardMobileNav({ badges }: Props) {
  const pathname = usePathname();

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  return (
    <nav
      className="pointer-events-none fixed inset-x-0 bottom-0 z-40 px-3 pb-[max(0.35rem,env(safe-area-inset-bottom,0px))] lg:hidden"
      aria-label="Навігація кабінету"
    >
      <div className="glass-liquid pointer-events-auto mx-auto flex h-[3.75rem] max-w-lg items-stretch justify-around gap-0.5 rounded-[28px] px-2 py-1.5">
        {mobileNav.map(({ href, icon: Icon, shortLabel, label, badgeKey, badgeAccent }) => {
          const active = isActive(href);
          const badge = badgeKey ? badges[badgeKey] : 0;
          const text = shortLabel ?? label;

          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "relative flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-[18px] px-1 py-1.5 transition-all",
                active
                  ? "bg-emerald/15 text-emerald-dark shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] ring-1 ring-emerald/30"
                  : "text-muted hover:bg-white/25 hover:text-ink",
              )}
            >
              <span className="relative">
                <Icon size={21} className={cn(active ? "text-emerald-dark" : "text-current")} />
                {badge > 0 && (
                  <span
                    className={cn(
                      "absolute -right-2 -top-1.5 min-w-[16px] rounded-full px-1 text-center text-[9px] font-bold leading-[16px]",
                      badgeAccent ? "bg-ink text-white" : "bg-emerald text-white",
                    )}
                  >
                    {badge > 99 ? "99+" : badge}
                  </span>
                )}
              </span>
              <span className={cn("text-[10px] font-semibold leading-none", active && "font-bold text-emerald-dark")}>
                {text}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
