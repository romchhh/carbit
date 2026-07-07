"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";
import { UserAvatar } from "@/components/ui/UserAvatar";
import { useAuth } from "@/contexts/AuthProvider";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { IconBell, IconArrowRight, IconX } from "@/components/icons";

const navLinks = [
  { href: "/", label: "Головна" },
  { href: "/#search", label: "Пошук" },
  { href: "/pricing", label: "Тарифи" },
  { href: "/#how-it-works", label: "Як це працює" },
];

export function Header() {
  const { user, logout } = useAuth();
  const isLoggedIn = !!user;
  const pathname = usePathname();
  const onHero = pathname === "/";
  const [heroInView, setHeroInView] = useState(onHero);
  const [menuOpen, setMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const transparent = onHero && heroInView;
  const lightHeader = transparent && !menuOpen;

  useEffect(() => {
    if (!onHero) {
      setHeroInView(false);
      return;
    }

    const hero = document.getElementById("landing-hero");
    if (!hero) {
      setHeroInView(false);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => setHeroInView(entry.isIntersecting),
      { threshold: 0 },
    );

    observer.observe(hero);
    return () => observer.disconnect();
  }, [onHero, pathname]);

  useEffect(() => {
    if (menuOpen) {
      lockBodyScroll();
      return () => unlockBodyScroll();
    }
    unlockBodyScroll();
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

  const scrollToSearch = () => {
    setMenuOpen(false);
    if (pathname === "/") {
      document.getElementById("search")?.scrollIntoView({ behavior: "smooth", block: "start" });
      window.history.replaceState(null, "", "#search");
      return true;
    }
    return false;
  };

  const handleNavClick = (href: string) => (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (href === "/#search" && scrollToSearch()) {
      e.preventDefault();
    } else if (menuOpen) {
      setMenuOpen(false);
    }
  };

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    if (href.includes("#")) return false;
    return pathname === href || pathname.startsWith(href + "/");
  };

  const navLinkClass = (href: string) => cn(
    "px-3.5 py-2 rounded-full text-[14px] transition-all duration-200",
    lightHeader
      ? isActive(href)
        ? "text-white font-semibold ring-1 ring-white/30 bg-white/10"
        : "text-white font-medium hover:text-white hover:ring-1 hover:ring-white/35 hover:bg-white/10"
      : menuOpen
        ? isActive(href)
          ? "text-emerald font-semibold ring-1 ring-emerald/40 bg-emerald/10"
          : "text-white hover:text-white hover:ring-1 hover:ring-white/35 hover:bg-white/10"
        : isActive(href)
          ? "text-ink font-semibold ring-1 ring-border bg-surface"
          : "text-muted hover:text-ink hover:ring-1 hover:ring-border hover:bg-surface/80"
  );

  const headerActionClass = cn(
    "inline-flex items-center justify-center rounded-full transition-all duration-200",
    lightHeader
      ? "hover:ring-1 hover:ring-white/35 hover:bg-white/10"
      : "hover:ring-1 hover:ring-border hover:bg-surface/80",
  );

  return (
    <>
      <header
        className={cn(
          "top-0 z-50 w-full transition-[background-color,border-color,box-shadow] duration-300",
          onHero ? "fixed" : "sticky",
          transparent
            ? "bg-transparent border-b border-transparent"
            : "bg-white border-b border-border shadow-sm shadow-black/[0.03]"
        )}
      >
        <div className={cn(
          "max-w-[1280px] mx-auto px-4 sm:px-6 h-[72px] sm:h-[80px] flex items-center lg:grid lg:grid-cols-[1fr_auto_1fr] lg:gap-4 transition-colors duration-500",
          lightHeader && "text-white"
        )}>
          <Link href="/" className="inline-flex items-center shrink-0 justify-self-start">
            <CarbitLogo variant="full" height={32} light={lightHeader} />
          </Link>

          <nav className="hidden lg:flex items-center justify-center gap-1.5">
            {navLinks.map(({ href, label }) => (
              <Link key={href} href={href} className={navLinkClass(href)} onClick={handleNavClick(href)}>
                {label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-2.5 ml-auto lg:ml-0 justify-self-end">
            {isLoggedIn && user ? (
              <>
                <Link href="/app/notifications" className={cn(
                  "relative flex w-11 h-11 items-center justify-center",
                  headerActionClass,
                  lightHeader ? "text-white" : "text-muted hover:text-ink"
                )}>
                  <IconBell size={21} />
                </Link>
                <div className="relative" ref={userMenuRef}>
                  <button
                    type="button"
                    onClick={() => setUserMenuOpen(v => !v)}
                    className={cn(
                      "flex items-center gap-2.5 rounded-full px-1.5 py-1",
                      headerActionClass,
                    )}
                    aria-expanded={userMenuOpen}
                    aria-haspopup="menu"
                  >
                    <span className="hidden sm:block text-[14px] font-medium max-w-[140px] truncate text-right">
                      <span className={lightHeader ? "text-white" : "text-ink"}>{user.name.split(" ")[0]}</span>
                    </span>
                    <UserAvatar
                      name={user.name}
                      avatarUrl={user.avatar_url}
                      className="h-11 w-11 text-[13px] font-bold tracking-wide shadow-md shadow-emerald/30"
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
                  "hidden sm:inline-flex text-[13px] px-4 py-2 font-medium",
                  headerActionClass,
                  lightHeader ? "text-white" : "text-muted hover:text-ink"
                )}>
                  Увійти
                </Link>
                <Link href="/auth/login" className={cn(
                  "hidden sm:inline-flex group items-center gap-2 text-[13px] font-semibold px-4 py-2 transition-all duration-300 hover:-translate-y-0.5",
                  lightHeader
                    ? "bg-white text-ink hover:bg-white/90 shadow-lg shadow-black/20 hover:ring-1 hover:ring-white/50"
                    : "bg-ink text-white hover:bg-ink-2 shadow-md shadow-ink/15 hover:ring-1 hover:ring-ink/25",
                  "rounded-full"
                )}>
                  Зареєструватися
                  <span className={cn(
                    "w-5 h-5 rounded-full flex items-center justify-center group-hover:translate-x-0.5 transition-transform",
                    lightHeader ? "bg-ink/10" : "bg-white/15"
                  )}>
                    <IconArrowRight size={12} />
                  </span>
                </Link>
              </>
            )}

            <button
              type="button"
              aria-label={menuOpen ? "Закрити меню" : "Відкрити меню"}
              aria-expanded={menuOpen}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setMenuOpen((v) => !v);
              }}
              className={cn(
                "lg:hidden relative z-10 w-10 h-10 rounded-full flex flex-col items-center justify-center gap-[4px] touch-manipulation select-none",
                headerActionClass,
                lightHeader
                  ? "bg-white/10 text-white"
                  : menuOpen
                    ? "bg-white/10 text-white"
                    : "bg-surface text-ink"
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

      {menuOpen && (
        <div
          className="fixed inset-0 z-[100] lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Навігація"
        >
          <div
            className="absolute inset-0 flex flex-col bg-ink"
          >
            <div className="flex items-center justify-between px-5 h-[72px] sm:h-[80px] border-b border-white/10 shrink-0">
              <Link href="/" className="flex items-center" onClick={() => setMenuOpen(false)}>
                <CarbitLogo variant="full" height={34} light />
              </Link>
              <button
                type="button"
                aria-label="Закрити меню"
                onClick={() => setMenuOpen(false)}
                className="w-10 h-10 rounded-full bg-white/10 hover:ring-1 hover:ring-white/35 text-white flex items-center justify-center transition-all touch-manipulation"
              >
                <IconX size={22} />
              </button>
            </div>

            <nav className="flex-1 flex flex-col justify-center px-5 py-8 overflow-y-auto overscroll-contain">
              {navLinks.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={handleNavClick(href)}
                  className="group flex items-center justify-between py-3.5 border-b border-white/10"
                >
                  <span className="text-[24px] sm:text-[28px] font-semibold text-white tracking-tight group-hover:text-emerald transition-colors">
                    {label}
                  </span>
                  <span className="w-8 h-8 rounded-full border border-white/20 flex items-center justify-center text-white/60 group-hover:bg-emerald group-hover:border-emerald group-hover:text-white transition-colors">
                    <IconArrowRight size={16} />
                  </span>
                </Link>
              ))}
            </nav>

            {!isLoggedIn ? (
              <div className="px-5 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-3 space-y-2 border-t border-white/10 shrink-0">
                <Link
                  href="/auth/login"
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center justify-center w-full py-3 rounded-full border border-white/25 text-white text-[14px] font-medium hover:ring-1 hover:ring-white/35 hover:bg-white/10 transition-all"
                >
                  Увійти
                </Link>
                <Link
                  href="/auth/login"
                  onClick={() => setMenuOpen(false)}
                  className="group flex items-center justify-center gap-2 w-full py-3 rounded-full bg-emerald text-white text-[14px] font-semibold hover:bg-emerald-dark hover:ring-1 hover:ring-emerald/50 shadow-lg shadow-emerald/30 transition-all"
                >
                  Зареєструватися
                  <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">
                    <IconArrowRight size={12} />
                  </span>
                </Link>
              </div>
            ) : (
              <div className="px-5 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-3 space-y-2 border-t border-white/10 shrink-0">
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
                  className="w-full py-2.5 rounded-full bg-white/10 text-white text-[13px] font-medium hover:bg-white/20 transition-colors touch-manipulation"
                >
                  Вийти
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
