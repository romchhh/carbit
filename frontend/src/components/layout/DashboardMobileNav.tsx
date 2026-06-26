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
      className="fixed inset-x-0 bottom-0 z-40 lg:hidden px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
      aria-label="Навігація кабінету"
    >
      <div className="mx-auto flex max-w-lg items-stretch justify-around gap-0.5 rounded-2xl border border-border/60 bg-white/95 px-1 py-1.5 shadow-[0_-4px_32px_-8px_rgba(10,12,14,0.12),0_8px_24px_-8px_rgba(10,12,14,0.08)] backdrop-blur-xl">
        {mobileNav.map(({ href, icon: Icon, shortLabel, label, badgeKey, badgeAccent }) => {
          const active = isActive(href);
          const badge = badgeKey ? badges[badgeKey] : 0;
          const text = shortLabel ?? label;

          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "relative flex min-w-0 flex-1 flex-col items-center gap-0.5 rounded-xl px-1 py-2 transition-colors",
                active ? "bg-emerald/10 text-emerald-dark" : "text-muted hover:text-ink",
              )}
            >
              <span className="relative">
                <Icon size={20} className={active ? "text-emerald-dark" : undefined} />
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
              <span className={cn("text-[10px] font-semibold leading-none", active && "text-emerald-dark")}>
                {text}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
