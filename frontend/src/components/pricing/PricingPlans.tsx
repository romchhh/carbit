import Link from "next/link";
import { cn } from "@/lib/utils";
import { PRICING_PLANS, type PricingPlan } from "@/lib/pricing-plans";
import { IconCheck, IconX } from "@/components/icons";

export type PricingCardModel = {
  id: string;
  name: string;
  description: string;
  price: string;
  period: string;
  features: string[];
  missing: string[];
  cta: string;
  href?: string;
  accent: boolean;
  popular: boolean;
  current?: boolean;
  loading?: boolean;
  disabled?: boolean;
};

type PricingPlansProps = {
  variant?: "home" | "page" | "cabinet";
  plans?: PricingCardModel[];
  onSelect?: (planId: string) => void;
};

function toCardModel(plan: PricingPlan): PricingCardModel {
  return {
    id: plan.id,
    name: plan.name,
    description: plan.description,
    price: plan.price,
    period: plan.period,
    features: plan.features,
    missing: plan.missing,
    cta: plan.cta,
    href: plan.href,
    accent: plan.accent,
    popular: plan.popular,
  };
}

export function PricingPlans({
  variant = "page",
  plans,
  onSelect,
}: PricingPlansProps) {
  const isHome = variant === "home" || variant === "cabinet";
  const isCabinet = variant === "cabinet";
  const cards = plans ?? PRICING_PLANS.map(toCardModel);

  return (
    <div
      className={cn(
        "grid gap-4 sm:gap-5",
        isHome
          ? "grid-cols-1 sm:grid-cols-2 xl:grid-cols-4"
          : "grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4",
      )}
    >
      {cards.map(plan => {
        const {
          id,
          name,
          description,
          price,
          period,
          features,
          missing,
          cta,
          href,
          accent,
          popular,
          current,
          loading,
          disabled,
        } = plan;

        const ctaClass = cn(
          "group flex w-full items-center justify-center gap-1.5 rounded-full text-center font-semibold transition-all duration-300",
          isHome ? "mt-5 py-2 text-[12px]" : "mb-8 py-3.5 text-[15px]",
          !disabled && !loading && "hover:-translate-y-0.5",
          disabled || loading
            ? accent
              ? "cursor-default bg-white/15 text-white/70"
              : "cursor-default bg-ink/10 text-muted"
            : accent
              ? "bg-emerald text-white shadow-lg shadow-emerald/30 hover:bg-white hover:text-ink hover:shadow-lg hover:shadow-white/20"
              : "bg-ink text-white shadow-lg shadow-ink/15 hover:bg-emerald hover:shadow-lg hover:shadow-emerald/30",
        );

        const arrow = (
          <span
            className={cn(
              "flex items-center justify-center rounded-full transition-all group-hover:translate-x-0.5",
              isHome ? "h-5 w-5 text-[10px]" : "h-7 w-7 text-[13px]",
              accent ? "bg-white/20 group-hover:bg-ink/10" : "bg-white/20",
            )}
          >
            →
          </span>
        );

        return (
          <article
            key={id}
            className={cn(
              "relative flex flex-col transition-all duration-300 hover:-translate-y-0.5",
              isHome ? "rounded-2xl p-5 sm:p-6" : "rounded-3xl p-8",
              accent
                ? isHome
                  ? "bg-ink text-white shadow-xl shadow-ink/30 ring-2 ring-emerald/50 xl:scale-[1.02]"
                  : "bg-ink text-white shadow-xl shadow-ink/25 ring-2 ring-emerald/50 xl:scale-[1.03] xl:-mt-2 xl:mb-2"
                : "border border-border/60 bg-surface shadow-sm hover:shadow-card",
              current && !accent && "ring-2 ring-emerald/40",
            )}
          >
            {(popular || current) && (
              <span
                className={cn(
                  "absolute left-1/2 -translate-x-1/2 rounded-full bg-emerald font-bold uppercase tracking-wider text-white shadow-lg shadow-emerald/30",
                  isHome ? "-top-3.5 px-3 py-1 text-[10px]" : "-top-3.5 px-4 py-1.5 text-[11px]",
                )}
              >
                {current ? "Поточний" : "Популярний"}
              </span>
            )}

            <h3
              className={cn(
                "font-semibold",
                isHome ? "text-[20px]" : "text-[22px] font-bold",
                accent ? "text-white" : "text-ink",
              )}
            >
              {name}
            </h3>

            <p
              className={cn(
                "mt-2 text-[12px] leading-snug",
                isHome ? "line-clamp-2" : "text-[13px]",
                accent ? "text-white/55" : "text-muted",
              )}
            >
              {description}
            </p>

            <div className={cn("flex items-end gap-1.5", isHome ? "mt-3" : "mt-5")}>
              <span
                className={cn(
                  "font-semibold leading-none tracking-tight",
                  isHome ? "text-[32px] sm:text-[36px]" : "text-[52px] font-black",
                  accent ? "text-emerald" : "text-ink",
                )}
              >
                {price}
              </span>
              {price !== "0" && (
                <span
                  className={cn(
                    "pb-1 text-[13px] font-medium sm:pb-2 sm:text-[15px]",
                    accent ? "text-white/40" : "text-muted",
                  )}
                >
                  грн
                </span>
              )}
            </div>

            <p
              className={cn(
                isHome ? "mt-1 text-[12px]" : "mb-8 mt-1 text-[14px]",
                accent ? "text-white/45" : "text-muted",
              )}
            >
              {period}
            </p>

            {isCabinet || onSelect ? (
              <button
                type="button"
                disabled={disabled || loading || current}
                onClick={() => onSelect?.(id)}
                className={ctaClass}
              >
                {loading ? "Зачекайте…" : current ? "Ваш тариф" : cta}
                {!current && !loading && arrow}
              </button>
            ) : (
              <Link href={href || "/auth/login"} className={ctaClass}>
                {cta}
                {arrow}
              </Link>
            )}

            <div className={cn("flex-1 space-y-2.5", isHome ? "mt-5" : "space-y-3.5")}>
              {features.map(f => (
                <div
                  key={f}
                  className={cn(
                    "flex gap-2",
                    isHome ? "text-[12px]" : "gap-3 text-[14px]",
                    accent ? "text-white/80" : "text-ink",
                  )}
                >
                  <IconCheck size={isHome ? 14 : 16} className="mt-0.5 shrink-0 text-emerald" />
                  {f}
                </div>
              ))}
              {missing.map(f => (
                <div
                  key={f}
                  className={cn(
                    "flex gap-2 opacity-50",
                    isHome ? "text-[12px] text-muted" : "gap-3 text-[14px] text-muted/50",
                  )}
                >
                  <IconX size={isHome ? 14 : 16} className="mt-0.5 shrink-0" />
                  {f}
                </div>
              ))}
            </div>
          </article>
        );
      })}
    </div>
  );
}
