"use client";

import Link from "next/link";
import { IconCreditCard, IconZap } from "@/components/icons";
import {
  formatPlanPrice,
  getPricingPlan,
  nextPaidPlanId,
  PAID_PLAN_ORDER,
  planDisplayName,
  planMonitorLimit,
} from "@/lib/plan-catalog";
import { cn } from "@/lib/utils";

type Variant = "banner" | "compact" | "sidebar";

type Props = {
  planId: string;
  searchesLimit: number;
  searchesUsed?: number;
  isTrial?: boolean;
  variant?: Variant;
  className?: string;
  /** Примусово показати навіть на pro (рідко потрібно). */
  force?: boolean;
};

export function SubscriptionPitch({
  planId,
  searchesLimit,
  searchesUsed = 0,
  isTrial = false,
  variant = "banner",
  className,
  force = false,
}: Props) {
  const isFree = planId === "free";
  const nextId = nextPaidPlanId(planId, searchesLimit);
  // Бізнес (pro) — верхній тариф: без апселу, але плашку з лімітом лишаємо.
  if (!force && !isFree && !nextId && planId === "pro" && variant === "banner") return null;

  const next = nextId ? getPricingPlan(nextId) : null;
  const remaining = Math.max(0, searchesLimit - searchesUsed);
  const nearLimit = remaining <= 2;

  if (variant === "sidebar") {
    return (
      <div className={cn("rounded-2xl bg-surface p-4", className)}>
        <div className="mb-1 text-[11px] font-bold uppercase tracking-[0.08em] text-muted">
          Тариф
        </div>
        <div className="text-[14px] font-black text-ink">
          {planDisplayName(planId)}
          {isTrial ? (
            <span className="ml-1 text-[11px] font-semibold text-emerald-dark">Trial</span>
          ) : null}
        </div>
        <div className="mt-2 mb-2 flex justify-between text-[12px]">
          <span className="text-muted">Моніторинги</span>
          <span className="font-semibold text-ink">
            {searchesUsed}/{searchesLimit}
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-border">
          <div
            className={cn(
              "h-full rounded-full transition-all",
              nearLimit ? "bg-amber-500" : "bg-emerald",
            )}
            style={{
              width: `${searchesLimit > 0 ? Math.min(100, Math.round((searchesUsed / searchesLimit) * 100)) : 0}%`,
            }}
          />
        </div>
        {isFree || isTrial ? (
          <p className="mt-3 text-[11px] leading-snug text-muted">
            {isTrial
              ? "Trial — 1 моніторинг. Старт — "
              : "1 моніторинг. Старт — "}
            {formatPlanPrice("lite")} · до 10. Про — {formatPlanPrice("standard")} · до 30.
          </p>
        ) : next ? (
          <p className="mt-3 text-[11px] leading-snug text-muted">
            Більше слотів: «{next.name}» — {formatPlanPrice(next.id)} / 30 днів · до{" "}
            {planMonitorLimit(next.id)} моніторингів.
          </p>
        ) : null}
        <Link
          href="/app/billing"
          className={cn(
            "mt-3 flex w-full items-center justify-center rounded-full px-3 py-2 text-[12px] font-bold transition-colors",
            isFree || nearLimit
              ? "bg-emerald text-white hover:bg-emerald-dark"
              : "bg-ink text-white hover:bg-emerald",
          )}
        >
          {isFree ? "Оформити підписку" : nearLimit ? "Збільшити ліміт" : "Тарифи та оплата"}
        </Link>
      </div>
    );
  }

  if (variant === "compact") {
    return (
      <Link
        href="/app/billing"
        className={cn(
          "inline-flex w-full items-center justify-center gap-2 rounded-full border border-border bg-white px-4 py-2.5 text-[13px] font-bold text-ink transition-colors hover:bg-surface",
          className,
        )}
      >
        <IconCreditCard size={14} />
        {isFree ? "Оформити підписку" : nearLimit ? "Збільшити ліміт" : "Підписка"}
      </Link>
    );
  }

  // banner
  return (
    <section
      className={cn(
        "overflow-hidden rounded-2xl border border-ink/10 bg-ink px-5 py-5 text-white sm:px-6",
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 max-w-xl">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald/20 px-2.5 py-1 text-[11px] font-semibold text-emerald">
            <IconZap size={12} />
            {isFree || isTrial ? "Без підписки обмежений доступ" : `Тариф «${planDisplayName(planId)}»`}
          </div>
          <h2 className="mt-3 text-[18px] font-black tracking-tight sm:text-[20px]">
            {isFree
              ? "Підключіть підписку — не пропустіть лоти"
              : next
                ? "Більше моніторингів — більше угод"
                : "Ваша підписка активна"}
          </h2>
          <p className="mt-2 text-[13px] leading-relaxed text-white/70">
            {isFree
              ? "Оплачуйте раз на 30 днів: автоматичний моніторинг AUTO.RIA і OLX, миттєві сповіщення в Telegram, анти-дубль на Про."
              : next
                ? `Зараз ${searchesLimit} активних пошуків. «${next.name}» дає до ${planMonitorLimit(next.id)} — від ${formatPlanPrice(next.id)} з урахуванням залишку поточного періоду.`
                : "До 100 моніторингів, пріоритетна обробка і командний доступ. Керуйте оплатою в один клік."}
          </p>
        </div>
        <Link
          href="/app/billing"
          className="inline-flex shrink-0 items-center gap-2 rounded-full bg-emerald px-5 py-3 text-[14px] font-black text-white shadow-lg shadow-emerald/30 transition hover:bg-white hover:text-ink"
        >
          <IconCreditCard size={16} />
          {isFree ? "Оформити підписку" : next ? `На «${next.name}»` : "Керувати"}
        </Link>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-3">
        {PAID_PLAN_ORDER.map(id => {
          const p = getPricingPlan(id);
          if (!p) return null;
          const current = id === planId;
          const highlight = id === (next?.id ?? "standard");
          return (
            <Link
              key={id}
              href="/app/billing"
              className={cn(
                "rounded-xl border px-3 py-3 transition",
                highlight
                  ? "border-emerald/50 bg-emerald/15"
                  : "border-white/10 bg-white/5 hover:bg-white/10",
              )}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[13px] font-bold">{p.name}</span>
                {current && (
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald">
                    ваш
                  </span>
                )}
              </div>
              <div className="mt-1 text-[15px] font-black text-emerald">
                {formatPlanPrice(id)}
                <span className="ml-1 text-[11px] font-medium text-white/50">/ 30 дн.</span>
              </div>
              <div className="mt-1 text-[11px] text-white/55">
                до {planMonitorLimit(id)} моніторингів
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
