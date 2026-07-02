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
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border/50 bg-white lg:hidden"
      style={{ paddingBottom: "var(--safe-bottom)" }}
      aria-label="Навігація кабінету"
    >
      <div className="mx-auto flex h-[3.75rem] max-w-lg items-stretch justify-around gap-0.5 px-1">
        {mobileNav.map(({ href, icon: Icon, shortLabel, label, badgeKey, badgeAccent }) => {
          const active = isActive(href);
          const badge = badgeKey ? badges[badgeKey] : 0;
          const text = shortLabel ?? label;

          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "relative flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-xl px-1 py-1 text-ink transition-colors",
                active ? "bg-surface" : "hover:bg-surface",
              )}
            >
              <span className="relative">
                <Icon size={20} className="text-ink" />
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
              <span className={cn("text-[10px] font-semibold leading-none text-ink", active && "font-bold")}>
                {text}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
