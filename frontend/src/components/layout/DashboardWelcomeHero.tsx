import Image from "next/image";
import Link from "next/link";
import { IconBell, IconZap } from "@/components/icons";
import { SOURCE_LOGOS } from "@/lib/brand-assets";
import { cn } from "@/lib/utils";

type Props = {
  firstName: string;
  activeSearches: number;
  searchesLimit: number;
  telegramConnected?: boolean;
  unreadNotifications?: number;
  className?: string;
};

export function DashboardWelcomeHero({
  firstName,
  activeSearches,
  searchesLimit,
  telegramConnected = false,
  unreadNotifications = 0,
  className,
}: Props) {
  const remaining = Math.max(0, searchesLimit - activeSearches);

  return (
    <section
      data-tour="welcome-hero"
      className={cn(
        "relative mb-8 overflow-hidden rounded-[1.35rem] border border-emerald/15",
        "bg-gradient-to-br from-emerald/[0.12] via-white to-surface/40",
        "px-5 py-5 shadow-[0_8px_32px_-16px_rgba(0,168,124,0.18)] sm:px-6 sm:py-6",
        className,
      )}
    >
      <div
        className="pointer-events-none absolute -right-10 -top-10 h-36 w-36 rounded-full bg-emerald/15 blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -bottom-12 left-1/3 h-28 w-28 rounded-full bg-emerald/5 blur-2xl"
        aria-hidden
      />

      <div className="relative">
        <h1 className="mt-1.5 text-[24px] font-black leading-tight tracking-tight text-ink sm:text-[30px]">
          Привіт,{" "}
          <span className="bg-gradient-to-r from-emerald-dark to-emerald bg-clip-text text-transparent">
            {firstName}
          </span>
        </h1>
        <p className="mt-2.5 max-w-[34rem] text-[13px] leading-relaxed text-muted sm:text-[14px]">
          Налаштуйте фільтри — Carbit моніторить{" "}
          <span className="font-medium text-ink">AUTO.RIA</span> і надсилає нові авто в{" "}
          <span className="font-medium text-ink">Telegram</span>
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-white/90 px-2.5 py-1.5 text-[11px] font-medium text-ink shadow-sm">
            <Image src={SOURCE_LOGOS.autoRia} alt="" width={18} height={18} className="rounded-full" />
            AUTO.RIA
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-white/90 px-2.5 py-1.5 text-[11px] font-medium text-ink shadow-sm">
            <Image src={SOURCE_LOGOS.telegram} alt="" width={18} height={18} className="rounded-full" />
            Telegram
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald/20 bg-emerald/10 px-2.5 py-1.5 text-[11px] font-semibold text-emerald-dark">
            <IconZap size={12} />
            {activeSearches} з {searchesLimit} моніторингів
          </span>
          {unreadNotifications > 0 && (
            <Link
              href="/app/notifications"
              className="inline-flex items-center gap-1 rounded-full border border-ink/10 bg-ink px-2.5 py-1.5 text-[11px] font-semibold text-white transition-opacity hover:opacity-90"
            >
              <IconBell size={12} />
              {unreadNotifications} нових
            </Link>
          )}
        </div>

        {!telegramConnected && (
          <p className="mt-3 text-[12px] text-muted">
            Підключіть Telegram у{" "}
            <Link href="/app/account" className="font-semibold text-emerald-dark hover:underline">
              акаунті
            </Link>
            , щоб отримувати сповіщення миттєво
            {remaining > 0 ? ` · ще ${remaining} слотів вільно` : ""}
          </p>
        )}
      </div>
    </section>
  );
}
