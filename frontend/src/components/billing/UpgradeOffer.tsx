"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, billing as billingApi } from "@/lib/api";
import { submitLiqPayCheckout } from "@/lib/liqpay-checkout";
import { Alert } from "@/components/ui/Alert";
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
        router.push("/app/billing/success");
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

  const heading =
    title ?? (quote ? `Перейдіть на «${quote.target_plan_name}»` : "Збільште ліміт моніторингів");

  return (
    <div className={cn("space-y-2", className)}>
      <Alert
        variant="warning"
        role="alert"
        title={heading}
        action={
          <button
            type="button"
            disabled={loading || fetching || !quote}
            onClick={() => void startCheckout()}
            className={cn(
              "inline-flex w-full items-center justify-center rounded-full bg-amber-600 px-4 py-2 text-[12px] font-bold text-white transition-colors hover:bg-amber-700 sm:w-auto",
              "disabled:cursor-not-allowed disabled:opacity-60",
              !compact && "sm:min-w-[180px] sm:px-5 sm:py-2.5 sm:text-[13px]",
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
        }
      >
        {fetching && <p>Рахуємо доплату…</p>}
        {quote && !fetching && (
          <div className="space-y-1">
            <p>
              До {quote.target_searches_limit} активних моніторингів · тариф{" "}
              <span className="font-semibold text-amber-950">
                {formatUah(quote.target_price_uah)}
              </span>{" "}
              / {quote.target_period_days} днів
            </p>
            {quote.credit_uah > 0 ? (
              <p>
                Залишок «{quote.current_plan_name}»: {quote.days_remaining} дн. ≈{" "}
                <span className="font-semibold text-amber-950">
                  {formatUah(quote.credit_uah)}
                </span>{" "}
                кредиту. Доплата сьогодні:{" "}
                <span className="font-bold text-amber-950">
                  {formatUah(quote.amount_due_uah)}
                </span>
                {!quote.enable_subscribe && <> · далі — повна ціна</>}
              </p>
            ) : quote.is_free_upgrade ? (
              <p className="font-semibold text-amber-950">
                Залишок повністю покриває апгрейд — без доплати.
              </p>
            ) : (
              <p>
                До сплати:{" "}
                <span className="font-bold text-amber-950">
                  {formatUah(quote.amount_due_uah)}
                </span>
              </p>
            )}
            <p>
              <Link
                href="/app/billing"
                className="font-semibold underline-offset-2 hover:underline"
              >
                Усі тарифи
              </Link>
            </p>
          </div>
        )}
      </Alert>
      {error && (
        <Alert variant="danger" role="alert" title="Не вдалося відкрити оплату">
          {error}
        </Alert>
      )}
    </div>
  );
}
