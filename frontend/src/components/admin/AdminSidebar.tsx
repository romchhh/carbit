"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { IconMenu, IconX } from "@/components/icons";
import { useAdminAuth } from "@/contexts/AdminAuthProvider";

const links = [
  { href: "/admin", label: "Дашборд", exact: true },
  { href: "/admin/system", label: "Система" },
  { href: "/admin/listings", label: "Оголошення" },
  { href: "/admin/parsing", label: "Парсинг" },
  { href: "/admin/requests", label: "API запити" },
  { href: "/admin/traffic", label: "Відвідування" },
  { href: "/admin/source-requests", label: "Заявки" },
  { href: "/admin/channels", label: "Telegram" },
  { href: "/admin/clients", label: "Клієнти" },
  { href: "/admin/subscriptions", label: "Підписки" },
  { href: "/admin/finance", label: "Фінанси" },
];

function NavLinks({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex-1 space-y-0.5 p-3">
      {links.map(({ href, label, exact }) => (
        <Link
          key={href}
          href={href}
          onClick={onNavigate}
          className={cn(
            "block rounded-lg px-3 py-2.5 text-[13px] transition-colors",
            (exact ? pathname === href : pathname.startsWith(href))
              ? "bg-white/10 font-semibold text-white"
              : "text-white/60 hover:bg-white/5 hover:text-white",
          )}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}

export function AdminSidebar() {
  const pathname = usePathname();
  const { logout } = useAdminAuth();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  const currentLabel =
    links.find(({ href, exact }) => (exact ? pathname === href : pathname.startsWith(href)))
      ?.label ?? "Admin";

  return (
    <>
      <header className="sticky top-0 z-40 flex items-center justify-between gap-3 border-b border-border bg-white/95 px-3 py-2.5 backdrop-blur lg:hidden">
        <button
          type="button"
          aria-label="Відкрити меню"
          onClick={() => setOpen(true)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-surface text-ink"
        >
          <IconMenu size={18} />
        </button>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13px] font-bold text-ink">{currentLabel}</div>
          <div className="text-[11px] text-muted">Carbit Admin</div>
        </div>
        <CarbitLogo variant="icon" height={28} />
      </header>

      {open ? (
        <button
          type="button"
          aria-label="Закрити меню"
          className="fixed inset-0 z-40 bg-ink/45 lg:hidden"
          onClick={() => setOpen(false)}
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[min(288px,86vw)] flex-col bg-ink text-white transition-transform duration-300 lg:static lg:z-auto lg:w-[220px] lg:translate-x-0 lg:shrink-0",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
      >
        <div className="flex items-center justify-between gap-3 border-b border-white/10 p-5">
          <div>
            <CarbitLogo variant="full" height={28} light />
            <div className="mt-2 text-[12px] font-semibold text-white/50">Admin</div>
          </div>
          <button
            type="button"
            aria-label="Закрити меню"
            onClick={() => setOpen(false)}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white lg:hidden"
          >
            <IconX size={16} />
          </button>
        </div>

        <NavLinks pathname={pathname} onNavigate={() => setOpen(false)} />

        <div className="border-t border-white/10 p-3">
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              void logout();
            }}
            className="w-full rounded-lg px-3 py-2.5 text-left text-[13px] text-white/60 transition-colors hover:bg-white/5 hover:text-white"
          >
            Вийти
          </button>
        </div>
      </aside>
    </>
  );
}
