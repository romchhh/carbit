import Image from "next/image";
import Link from "next/link";
import { IconBell, IconCreditCard, IconZap } from "@/components/icons";
import { SOURCE_LOGOS } from "@/lib/brand-assets";
import { formatPlanPrice, planDisplayName } from "@/lib/plan-catalog";
import { cn } from "@/lib/utils";

type Props = {
  firstName: string;
  activeSearches: number;
  searchesLimit: number;
  planId: string;
  isTrial?: boolean;
  telegramConnected?: boolean;
  unreadNotifications?: number;
  className?: string;
};

export function DashboardWelcomeHero({
  firstName,
  activeSearches,
  searchesLimit,
  planId,
  isTrial = false,
  telegramConnected = false,
  unreadNotifications = 0,
  className,
}: Props) {
  const remaining = Math.max(0, searchesLimit - activeSearches);
  const isFree = planId === "free";
  const nearLimit = remaining <= 2;

  return (
    <section
      data-tour="welcome-hero"
      className={cn(
        "relative mb-5 overflow-hidden rounded-2xl sm:mb-8 sm:rounded-[1.35rem]",
        // Mobile: чистий світлий фон. Desktop: м’який wash без «плям».
        "border border-border/60 bg-white sm:border-emerald/15",
        "sm:bg-[linear-gradient(160deg,#f3fcf8_0%,#ffffff_42%,#f7f8fa_100%)]",
        "px-3.5 py-3.5 sm:px-6 sm:py-6",
        "sm:shadow-[0_8px_28px_-18px_rgba(0,164,124,0.22)]",
        className,
      )}
    >
      <div
        className="pointer-events-none absolute inset-y-0 right-0 hidden w-1/2 bg-[radial-gradient(ellipse_at_top_right,rgba(0,200,150,0.14),transparent_60%)] sm:block"
        aria-hidden
      />

      <div className="relative">
        {/* Мобільний варіант — лише привітання */}
        <h1 className="text-[22px] font-black leading-tight tracking-tight text-ink sm:hidden">
          Привіт, <span className="text-emerald-dark">{firstName}</span>
        </h1>

        {/* Desktop / планшет — повний блок */}
        <div className="hidden sm:block">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald/25 bg-white/90 px-2.5 py-1 text-[11px] font-semibold text-emerald-dark">
              <IconZap size={12} />
              {planDisplayName(planId)}
              {isTrial ? " · Trial" : ""}
            </span>
            {(isFree || nearLimit) && (
              <Link
                href="/app/billing"
                className="inline-flex items-center gap-1 rounded-full bg-ink px-2.5 py-1 text-[11px] font-bold text-white transition hover:bg-emerald-dark"
              >
                <IconCreditCard size={12} />
                {isFree ? `Підписка від ${formatPlanPrice("lite")}` : "Збільшити ліміт"}
              </Link>
            )}
          </div>

          <h1 className="mt-2.5 text-[30px] font-black leading-tight tracking-tight text-ink">
            Привіт, <span className="text-emerald-dark">{firstName}</span>
          </h1>
          <p className="mt-2.5 max-w-[34rem] text-[14px] leading-relaxed text-muted">
            Налаштуйте фільтри — Carbit моніторить{" "}
            <span className="font-medium text-ink">AUTO.RIA</span>,{" "}
            <span className="font-medium text-ink">OLX</span> і надсилає нові авто в{" "}
            <span className="font-medium text-ink">Telegram</span>
            {isFree ? (
              <>
                . На безкоштовному тарифі — до {searchesLimit} моніторингу; Старт дає 10 за{" "}
                {formatPlanPrice("lite")}
              </>
            ) : null}
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-white/90 px-2.5 py-1.5 text-[11px] font-medium text-ink shadow-sm">
              <Image
                src={SOURCE_LOGOS.autoRia}
                alt=""
                width={18}
                height={18}
                className="h-[18px] w-[18px] rounded-full object-contain"
              />
              AUTO.RIA
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-white/90 px-2.5 py-1.5 text-[11px] font-medium text-ink shadow-sm">
              <Image
                src={SOURCE_LOGOS.olx}
                alt=""
                width={18}
                height={18}
                className="h-[18px] w-[18px] rounded-full object-contain"
              />
              OLX
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-white/90 px-2.5 py-1.5 text-[11px] font-medium text-ink shadow-sm">
              <Image
                src={SOURCE_LOGOS.telegram}
                alt=""
                width={18}
                height={18}
                className="h-[18px] w-[18px] rounded-full object-contain"
              />
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
      </div>
    </section>
  );
}
