import Link from "next/link";
import { cn } from "@/lib/utils";
import { PRICING_PLANS } from "@/lib/pricing-plans";
import { IconCheck, IconX } from "@/components/icons";

type PricingPlansProps = {
  variant?: "home" | "page";
};

export function PricingPlans({ variant = "page" }: PricingPlansProps) {
  const isHome = variant === "home";

  return (
    <div
      className={cn(
        "grid gap-4 sm:gap-5",
        isHome
          ? "grid-cols-1 sm:grid-cols-2 xl:grid-cols-4"
          : "grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6",
      )}
    >
      {PRICING_PLANS.map(({ name, price, period, features, missing, cta, href, accent, popular }) => (
        <article
          key={name}
          className={cn(
            "relative flex flex-col transition-all duration-300 hover:-translate-y-0.5",
            isHome ? "rounded-2xl p-5 sm:p-6" : "rounded-3xl p-8",
            accent
              ? isHome
                ? "bg-ink text-white shadow-xl shadow-ink/30 ring-2 ring-emerald/50 xl:scale-[1.02]"
                : "bg-ink text-white shadow-xl shadow-ink/25 ring-2 ring-emerald/50 xl:scale-[1.03] xl:-mt-2 xl:mb-2"
              : "card-rounded",
          )}
        >
          {popular && (
            <span
              className={cn(
                "absolute -top-3.5 left-1/2 -translate-x-1/2 bg-emerald text-white font-bold uppercase tracking-wider rounded-full shadow-lg shadow-emerald/30",
                isHome ? "text-[10px] px-3 py-1" : "text-[11px] px-4 py-1.5",
              )}
            >
              Популярний
            </span>
          )}

          <h3 className={cn("font-semibold", isHome ? "text-[20px]" : "text-[22px] font-bold", accent ? "text-white" : "text-ink")}>
            {name}
          </h3>

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
            {price !== "0" && !isHome && (
              <span className={cn("pb-2 text-[15px] font-medium", accent ? "text-white/40" : "text-muted")}>грн</span>
            )}
          </div>

          <p className={cn(isHome ? "mt-1 text-[12px]" : "text-[14px] mt-1 mb-8", accent ? "text-white/45" : "text-muted")}>
            {period}
          </p>

          <Link
            href={href}
            className={cn(
              "group flex items-center justify-center gap-1.5 text-center font-medium rounded-full transition-all duration-300 hover:-translate-y-0.5",
              isHome ? "mt-5 text-[12px] py-2" : "text-[15px] font-semibold py-3.5 mb-8",
              accent
                ? "bg-emerald text-white hover:bg-emerald-dark shadow-lg shadow-emerald/30"
                : isHome
                  ? "bg-surface border border-border text-ink hover:bg-emerald hover:text-white hover:border-emerald"
                  : "border border-border text-ink hover:bg-emerald hover:text-white hover:border-emerald",
            )}
          >
            {cta}
            <span
              className={cn(
                "rounded-full flex items-center justify-center transition-all group-hover:translate-x-0.5",
                isHome ? "w-5 h-5 text-[10px]" : "w-7 h-7 text-[13px]",
                accent ? "bg-white/20" : "bg-ink/5 group-hover:bg-white/20",
              )}
            >
              →
            </span>
          </Link>

          <div className={cn("space-y-2.5 flex-1", isHome ? "mt-5" : "space-y-3.5")}>
            {features.map(f => (
              <div
                key={f}
                className={cn("flex gap-2", isHome ? "text-[12px]" : "text-[14px] gap-3", accent ? "text-white/80" : "text-ink")}
              >
                <IconCheck size={isHome ? 14 : 16} className="text-emerald shrink-0 mt-0.5" />
                {f}
              </div>
            ))}
            {missing.map(f => (
              <div
                key={f}
                className={cn(
                  "flex gap-2 opacity-50",
                  isHome ? "text-[12px] text-muted" : "text-[14px] text-muted/50 gap-3",
                )}
              >
                <IconX size={isHome ? 14 : 16} className="shrink-0 mt-0.5" />
                {f}
              </div>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}
