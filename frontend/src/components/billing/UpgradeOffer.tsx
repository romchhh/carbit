"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, billing as billingApi } from "@/lib/api";
import { submitLiqPayCheckout } from "@/lib/liqpay-checkout";
import { cn } from "@/lib/utils";
import type { UpgradeQuote } from "@/types/api";

type Props = {
  /** Показати блок одразу (ліміт / без підписки). */
  open?: boolean;
  compact?: boolean;
  className?: string;
  /** Якщо не задано — бекенд обере рекомендований план. */
  planId?: string;
  title?: string;
  onDone?: () => void;
};

function formatUah(n: number) {
  return `${n.toLocaleString("uk-UA")} грн`;
}

export function UpgradeOffer({
  open = true,
  compact,
  className,
  planId,
  title,
  onDone,
}: Props) {
  const router = useRouter();
  const [quote, setQuote] = useState<UpgradeQuote | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setFetching(true);
    setError("");
    billingApi
      .upgradeQuote(planId)
      .then(q => {
        if (!cancelled) setQuote(q);
      })
      .catch(err => {
        if (!cancelled) {
          setQuote(null);
          setError(err instanceof ApiError ? err.message : "Не вдалося порахувати апгрейд");
        }
      })
      .finally(() => {
        if (!cancelled) setFetching(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, planId]);

  const startCheckout = useCallback(async () => {
    if (!quote) return;
    setLoading(true);
    setError("");
    try {
      const checkout = await billingApi.checkout(quote.target_plan, true);
      if (checkout.free_upgrade) {
        onDone?.();
        router.push("/app/billing?paid=1");
        router.refresh();
        return;
      }
      submitLiqPayCheckout(checkout.checkout_url, checkout.data, checkout.signature);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося відкрити оплату");
      setLoading(false);
    }
  }, [quote, onDone, router]);

  if (!open) return null;

  return (
    <div
      className={cn(
        "rounded-2xl border border-emerald/25 bg-emerald-light/40 px-4 py-4 sm:px-5",
        className,
      )}
    >
      <p className="text-[14px] font-bold text-ink">
        {title ?? (quote ? `Перейдіть на «${quote.target_plan_name}»` : "Збільште ліміт моніторингів")}
      </p>

      {fetching && <p className="mt-2 text-[12px] text-muted">Рахуємо доплату…</p>}

      {quote && !fetching && (
        <div className={cn("mt-2 space-y-1.5 text-[12px] leading-snug text-muted", compact && "space-y-1")}>
          <p>
            До {quote.target_searches_limit} активних моніторингів · тариф{" "}
            <span className="font-semibold text-ink">{formatUah(quote.target_price_uah)}</span> /{" "}
            {quote.target_period_days} днів
          </p>
          {quote.credit_uah > 0 ? (
            <p>
              Залишок «{quote.current_plan_name}»: {quote.days_remaining} дн. ≈{" "}
              <span className="font-semibold text-ink">{formatUah(quote.credit_uah)}</span> кредиту
              (ціна ÷ {quote.period_days} × дні). Доплата сьогодні:{" "}
              <span className="font-bold text-emerald-dark">{formatUah(quote.amount_due_uah)}</span>
              {!quote.enable_subscribe && (
                <> · потім повна ціна перед наступним періодом</>
              )}
            </p>
          ) : quote.is_free_upgrade ? (
            <p className="font-semibold text-emerald-dark">Залишок повністю покриває апгрейд — без доплати.</p>
          ) : (
            <p>
              До сплати:{" "}
              <span className="font-bold text-emerald-dark">{formatUah(quote.amount_due_uah)}</span>
            </p>
          )}
        </div>
      )}

      {error && <p className="mt-2 text-[12px] font-medium text-red-600">{error}</p>}

      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <button
          type="button"
          disabled={loading || fetching || !quote}
          onClick={() => void startCheckout()}
          className={cn(
            "inline-flex items-center justify-center rounded-full bg-emerald px-5 py-2.5 text-[13px] font-bold text-white transition-colors hover:bg-emerald-dark",
            "disabled:cursor-not-allowed disabled:opacity-60",
            !compact && "w-full sm:w-auto sm:min-w-[200px] py-3 text-[14px]",
          )}
        >
          {loading
            ? "Відкриваємо оплату…"
            : quote?.is_free_upgrade
              ? "Активувати апгрейд"
              : quote
                ? `Оформити · ${formatUah(quote.amount_due_uah)}`
                : "Оформити підписку"}
        </button>
        <Link
          href="/app/billing"
          className="text-center text-[12px] font-semibold text-emerald-dark underline-offset-2 hover:underline sm:text-left"
        >
          Усі тарифи
        </Link>
      </div>
    </div>
  );
}
