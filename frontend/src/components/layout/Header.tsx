"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { UserAvatar } from "@/components/ui/UserAvatar";
import { useAuth } from "@/contexts/AuthProvider";
import { LogoIcon } from "@/components/brand/LogoIcon";
import { IconBell, IconArrowRight, IconX } from "@/components/icons";

const navLinks = [
  { href: "/", label: "Головна" },
  { href: "/app/search", label: "Пошук" },
  { href: "/pricing", label: "Тарифи" },
  { href: "/#how-it-works", label: "Як це працює" },
];

export function Header() {
  const { user, logout } = useAuth();
  const isLoggedIn = !!user;
  const pathname = usePathname();
  const onHero = pathname === "/";
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const transparent = onHero && !scrolled;
  const lightHeader = transparent && !menuOpen;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 48);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [menuOpen]);

  useEffect(() => {
    setMenuOpen(false);
    setUserMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    if (href.includes("#")) return false;
    return pathname === href || pathname.startsWith(href + "/");
  };

  const navLinkClass = (href: string) => cn(
    "px-3 py-1.5 rounded-full text-[13px] transition-all duration-200",
    lightHeader
      ? isActive(href) ? "text-white font-semibold" : "text-white font-medium hover:text-white/80"
      : menuOpen
        ? isActive(href) ? "text-emerald font-semibold" : "text-white hover:text-white/80"
        : isActive(href) ? "text-ink font-semibold" : "text-muted hover:text-ink"
  );

  return (
    <>
      <header
        className={cn(
          "top-0 z-50 w-full transition-all duration-500",
          onHero ? "fixed" : "sticky",
          transparent
            ? "bg-transparent border-b border-transparent"
            : "bg-white/95 backdrop-blur-xl border-b border-border shadow-sm shadow-black/[0.03]"
        )}
      >
        <div className={cn(
          "max-w-[1280px] mx-auto px-5 sm:px-6 h-[64px] sm:h-[72px] flex items-center lg:grid lg:grid-cols-[1fr_auto_1fr] lg:gap-4 transition-colors duration-500",
          lightHeader && "text-white"
        )}>
          <Link href="/" className="flex items-center gap-3 group shrink-0">
            <span className={cn(
              "w-8 h-8 sm:w-9 sm:h-9 rounded-full flex items-center justify-center transition-all duration-300 group-hover:scale-105",
              lightHeader ? "bg-white/10 ring-1 ring-white/20" : "bg-emerald-light ring-1 ring-emerald/20"
            )}>
              <LogoIcon size={22} light={lightHeader} />
            </span>
            <span className={cn("text-[15px] font-semibold tracking-tight", lightHeader ? "text-white" : "text-ink")}>
              Carbit
            </span>
          </Link>

          <nav className="hidden lg:flex items-center justify-center gap-1">
            {navLinks.map(({ href, label }) => (
              <Link key={href} href={href} className={navLinkClass(href)}>
                {label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-2 ml-auto lg:ml-0 justify-self-end">
            {isLoggedIn && user ? (
              <>
                <Link href="/app/notifications" className={cn(
                  "relative w-10 h-10 flex items-center justify-center rounded-full transition-all duration-200",
                  lightHeader ? "hover:bg-white/10 text-white" : "hover:bg-surface text-muted hover:text-ink"
                )}>
                  <IconBell size={20} />
                </Link>
                <div className="relative" ref={userMenuRef}>
                  <button
                    type="button"
                    onClick={() => setUserMenuOpen(v => !v)}
                    className="flex items-center gap-2 rounded-full hover:opacity-90 transition-opacity"
                    aria-expanded={userMenuOpen}
                    aria-haspopup="menu"
                  >
                    <span className="hidden sm:block text-[13px] font-medium max-w-[120px] truncate text-right">
                      <span className={lightHeader ? "text-white" : "text-ink"}>{user.name.split(" ")[0]}</span>
                    </span>
                    <UserAvatar
                      name={user.name}
                      avatarUrl={user.avatar_url}
                      className="h-10 w-10 text-[12px] font-bold tracking-wide shadow-md shadow-emerald/30"
                    />
                  </button>
                  {userMenuOpen && (
                    <div className="absolute right-0 top-full mt-2 w-56 bg-white border border-border rounded-xl shadow-lg py-1.5 z-50">
                      <div className="px-4 py-2.5 border-b border-border">
                        <div className="text-[13px] font-semibold text-ink truncate">{user.name}</div>
                        <div className="text-[11px] text-muted truncate mt-0.5">{user.email}</div>
                      </div>
                      <Link
                        href="/app/dashboard"
                        className="block px-4 py-2 text-[13px] text-ink hover:bg-surface transition-colors"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        Мої пошуки
                      </Link>
                      <Link
                        href="/app/account"
                        className="block px-4 py-2 text-[13px] text-ink hover:bg-surface transition-colors"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        Акаунт
                      </Link>
                      <button
                        type="button"
                        onClick={() => { setUserMenuOpen(false); logout(); }}
                        className="w-full text-left px-4 py-2 text-[13px] text-red-600 hover:bg-red-50 transition-colors"
                      >
                        Вийти
                      </button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                <Link href="/auth/login" className={cn(
                  "hidden sm:inline-flex text-[12px] px-3 py-1.5 rounded-full transition-all duration-200",
                  lightHeader ? "text-white hover:bg-white/10" : "text-muted hover:text-ink hover:bg-surface"
                )}>
                  Увійти
                </Link>
                <Link href="/auth/login" className={cn(
                  "hidden sm:inline-flex group items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-full transition-all duration-300 hover:-translate-y-0.5",
                  lightHeader
                    ? "bg-white text-ink hover:bg-white/90 shadow-lg shadow-black/20"
                    : "bg-ink text-white hover:bg-ink-2 shadow-md shadow-ink/15"
                )}>
                  Спробувати
                  <span className={cn(
                    "w-5 h-5 rounded-full flex items-center justify-center group-hover:translate-x-0.5 transition-transform",
                    lightHeader ? "bg-ink/10" : "bg-white/15"
                  )}>
                    <IconArrowRight size={11} />
                  </span>
                </Link>
              </>
            )}

            <button
              type="button"
              aria-label={menuOpen ? "Закрити меню" : "Відкрити меню"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(v => !v)}
              className={cn(
                "lg:hidden relative w-9 h-9 rounded-full flex flex-col items-center justify-center gap-[4px] transition-all duration-300",
                lightHeader
                  ? "bg-white/10 hover:bg-white/20 text-white"
                  : menuOpen
                    ? "bg-white/10 text-white"
                    : "bg-surface hover:bg-border/60 text-ink"
              )}
            >
              <span className={cn(
                "block h-[2px] rounded-full bg-current transition-all duration-300 origin-center",
                menuOpen ? "w-5 translate-y-[7px] rotate-45" : "w-5"
              )} />
              <span className={cn(
                "block h-[2px] rounded-full bg-current transition-all duration-300",
                menuOpen ? "w-0 opacity-0" : "w-5"
              )} />
              <span className={cn(
                "block h-[2px] rounded-full bg-current transition-all duration-300 origin-center",
                menuOpen ? "w-5 -translate-y-[7px] -rotate-45" : "w-5"
              )} />
            </button>
          </div>
        </div>
      </header>

      <div
        className={cn(
          "fixed inset-0 z-[60] lg:hidden transition-all duration-500",
          menuOpen ? "visible pointer-events-auto" : "invisible pointer-events-none"
        )}
        aria-hidden={!menuOpen}
      >
        <div
          className={cn(
            "absolute inset-0 bg-ink/60 backdrop-blur-sm transition-opacity duration-500",
            menuOpen ? "opacity-100" : "opacity-0"
          )}
          onClick={() => setMenuOpen(false)}
        />
        <div
          className={cn(
            "absolute inset-0 bg-ink flex flex-col transition-all duration-500 ease-out",
            menuOpen ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4"
          )}
        >
          <div className="flex items-center justify-between px-5 h-[64px] sm:h-[72px] border-b border-white/10">
            <Link href="/" className="flex items-center gap-2.5" onClick={() => setMenuOpen(false)}>
              <span className="w-8 h-8 rounded-full bg-white/10 ring-1 ring-white/20 flex items-center justify-center">
                <LogoIcon size={22} light />
              </span>
              <span className="text-[15px] font-semibold text-white">Carbit</span>
            </Link>
            <button
              type="button"
              aria-label="Закрити меню"
              onClick={() => setMenuOpen(false)}
              className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
            >
              <IconX size={22} />
            </button>
          </div>

          <nav className="flex-1 flex flex-col justify-center px-5 py-8">
            {navLinks.map(({ href, label }, i) => (
              <Link
                key={href}
                href={href}
                onClick={() => setMenuOpen(false)}
                className={cn(
                  "group flex items-center justify-between py-3.5 border-b border-white/10 transition-all duration-300",
                  menuOpen ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-4"
                )}
                style={{ transitionDelay: menuOpen ? `${i * 60 + 100}ms` : "0ms" }}
              >
                <span className="text-[24px] sm:text-[28px] font-semibold text-white tracking-tight group-hover:text-emerald transition-colors">
                  {label}
                </span>
                <span className="w-8 h-8 rounded-full border border-white/20 flex items-center justify-center text-white/60 group-hover:bg-emerald group-hover:border-emerald group-hover:text-white transition-all duration-300 group-hover:translate-x-1">
                  <IconArrowRight size={16} />
                </span>
              </Link>
            ))}
          </nav>

          {!isLoggedIn ? (
            <div className="px-5 pb-6 pt-3 space-y-2 border-t border-white/10">
              <Link
                href="/auth/login"
                onClick={() => setMenuOpen(false)}
                className="flex items-center justify-center w-full py-2.5 rounded-full border border-white/25 text-white text-[13px] font-medium hover:bg-white/10 transition-colors"
              >
                Увійти
              </Link>
              <Link
                href="/auth/login"
                onClick={() => setMenuOpen(false)}
                className="group flex items-center justify-center gap-2 w-full py-2.5 rounded-full bg-emerald text-white text-[13px] font-medium hover:bg-emerald-dark shadow-lg shadow-emerald/30 transition-all"
              >
                Спробувати безкоштовно
                <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center group-hover:translate-x-0.5 transition-transform">
                  <IconArrowRight size={12} />
                </span>
              </Link>
            </div>
          ) : (
            <div className="px-5 pb-6 pt-3 space-y-2 border-t border-white/10">
              <div className="text-white/60 text-[12px] px-2 mb-1">{user?.name}</div>
              <Link
                href="/app/account"
                onClick={() => setMenuOpen(false)}
                className="flex items-center justify-center w-full py-2.5 rounded-full border border-white/25 text-white text-[13px] font-medium hover:bg-white/10 transition-colors"
              >
                Акаунт
              </Link>
              <button
                type="button"
                onClick={() => { setMenuOpen(false); logout(); }}
                className="w-full py-2.5 rounded-full bg-white/10 text-white text-[13px] font-medium hover:bg-white/20 transition-colors"
              >
                Вийти
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
