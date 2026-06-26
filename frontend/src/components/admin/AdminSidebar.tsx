"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAdminAuth } from "@/contexts/AdminAuthProvider";

const links = [
  { href: "/admin", label: "Дашборд", exact: true },
  { href: "/admin/clients", label: "Клієнти" },
  { href: "/admin/subscriptions", label: "Підписки" },
  { href: "/admin/finance", label: "Фінанси" },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const { logout } = useAdminAuth();

  return (
    <aside className="w-[220px] shrink-0 bg-ink text-white min-h-screen flex flex-col">
      <div className="p-5 border-b border-white/10">
        <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-white/40">Carbit</div>
        <div className="text-[16px] font-bold mt-0.5">Admin</div>
      </div>
      <nav className="flex-1 p-3 space-y-0.5">
        {links.map(({ href, label, exact }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "block px-3 py-2.5 rounded-lg text-[13px] transition-colors",
              (exact ? pathname === href : pathname.startsWith(href))
                ? "bg-white/10 text-white font-semibold"
                : "text-white/60 hover:text-white hover:bg-white/5",
            )}
          >
            {label}
          </Link>
        ))}
      </nav>
      <div className="p-3 border-t border-white/10">
        <button
          onClick={logout}
          className="w-full px-3 py-2.5 rounded-lg text-[13px] text-white/60 hover:text-white hover:bg-white/5 transition-colors text-left"
        >
          Вийти
        </button>
      </div>
    </aside>
  );
}
