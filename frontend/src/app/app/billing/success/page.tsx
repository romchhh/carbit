"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { LiqPayLogo } from "@/components/brand/LiqPayLogo";
import { IconCheck, IconCreditCard } from "@/components/icons";
import { CtaLink } from "@/components/ui/CtaLink";
import { useAuth } from "@/contexts/AuthProvider";
import { billing as billingApi } from "@/lib/api";
import { formatKyivDate, formatKyivDateTime } from "@/lib/datetime";
import { trackMetaPurchase } from "@/lib/meta-pixel";
import type { BillingPayment, Subscription } from "@/types/api";

function formatMoney(amount: number, currency = "UAH"): string {
  const code = currency.toUpperCase();
  const suffix = code === "UAH" ? "грн" : code;
  return `${amount.toLocaleString("uk-UA")} ${suffix}`;
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/60 py-3 last:border-b-0">
      <span className="text-[13px] text-muted">{label}</span>
      <span className="max-w-[60%] text-right text-[13px] font-semibold text-ink">{value}</span>
    </div>
  );
}

export default function PaymentSuccessPage() {
  const { refreshUser } = useAuth();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const purchaseTracked = useRef(false);

  const load = useCallback(async () => {
    try {
      const [sub] = await Promise.all([
        billingApi.subscription(),
        refreshUser().catch(() => undefined),
      ]);
      setSubscription(sub);
      return sub;
    } catch {
      return null;
    } finally {
      setLoading(false);
    }
  }, [refreshUser]);

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;

    const tick = async () => {
      const sub = await load();
      if (cancelled) return;
      const latest = sub?.payments?.[0];
      const ready =
        Boolean(sub && sub.plan !== "free") &&
        (Boolean(latest) || Boolean(sub?.card_mask) || Boolean(sub?.next_payment_at));
      attempts += 1;
      if (!ready && attempts < 8) {
        window.setTimeout(() => {
          if (!cancelled) void tick();
        }, 1500);
      }
    };

    void tick();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const latestPayment: BillingPayment | null = useMemo(() => {
    const payments = subscription?.payments ?? [];
    if (!payments.length) return null;
    return [...payments].sort(
      (a, b) => new Date(b.paid_at).getTime() - new Date(a.paid_at).getTime(),
    )[0];
  }, [subscription]);

  const planName = subscription?.plan_name ?? latestPayment?.plan_name ?? "—";
  const amountLabel = latestPayment
    ? formatMoney(latestPayment.amount, latestPayment.currency)
    : null;
  const cardMask = subscription?.card_mask || latestPayment?.card_mask || null;
  const paidAt = latestPayment?.paid_at ?? null;
  const nextPayment = subscription?.next_payment_at ?? subscription?.plan_expires_at ?? null;
  const recurring = Boolean(subscription?.recurring_active);

  useEffect(() => {
    if (!latestPayment || latestPayment.status !== "success" || purchaseTracked.current) return;
    purchaseTracked.current = true;
    trackMetaPurchase({
      value: latestPayment.amount,
      currency: latestPayment.currency,
      contentName: latestPayment.plan_name,
      contentIds: [latestPayment.plan],
      orderId: latestPayment.order_id,
      paymentId: latestPayment.liqpay_payment_id,
    });
  }, [latestPayment]);

  return (
    <div className="relative mx-auto w-full max-w-lg px-1 py-6 sm:py-10">
      <div
        className="pointer-events-none absolute inset-x-0 -top-6 h-56 bg-[radial-gradient(ellipse_at_50%_0%,rgba(0,200,150,0.2),transparent_60%)]"
        aria-hidden
      />

      <div className="relative">
        <div className="mb-6 flex items-center justify-between gap-3">
          <Link href="/app/dashboard" className="inline-flex">
            <CarbitLogo variant="full" height={28} />
          </Link>
          <LiqPayLogo height={20} className="opacity-80" />
        </div>

        <div className="rounded-[28px] border border-border/70 bg-white p-5 shadow-sm sm:p-7">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald text-white shadow-md shadow-emerald/25">
              <IconCheck size={22} />
            </div>
            <div className="min-w-0">
              <h1 className="text-[22px] font-black tracking-tight text-ink sm:text-[26px]">
                Оплату прийнято
              </h1>
              <p className="mt-1.5 text-[13px] leading-relaxed text-muted sm:text-[14px]">
                Дякуємо! Підписка активна. Нижче — деталі платежу та наступного списання.
              </p>
            </div>
          </div>

          {loading && !subscription ? (
            <div className="mt-8 flex justify-center py-10">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
            </div>
          ) : (
            <>
              <div className="mt-6 rounded-2xl border border-emerald/20 bg-emerald/5 px-4 py-4 sm:px-5">
                <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-emerald-dark">
                  Тариф
                </div>
                <div className="mt-1 flex flex-wrap items-end justify-between gap-2">
                  <div className="text-[20px] font-black text-ink sm:text-[22px]">{planName}</div>
                  {amountLabel && (
                    <div className="text-[20px] font-black tabular-nums text-emerald-dark sm:text-[22px]">
                      {amountLabel}
                    </div>
                  )}
                </div>
                {subscription?.searches_limit != null && (
                  <p className="mt-1 text-[12px] text-muted">
                    До {subscription.searches_limit} активних моніторингів
                  </p>
                )}
              </div>

              <div className="mt-2 px-1">
                <DetailRow
                  label="Статус"
                  value={<span className="text-emerald-dark">Успішно</span>}
                />
                {paidAt && (
                  <DetailRow label="Дата оплати" value={formatKyivDateTime(paidAt)} />
                )}
                {amountLabel && <DetailRow label="Сума" value={amountLabel} />}
                {cardMask && (
                  <DetailRow
                    label="Картка"
                    value={
                      <span className="inline-flex items-center gap-1.5">
                        <IconCreditCard size={14} className="text-muted" />
                        {cardMask}
                      </span>
                    }
                  />
                )}
                <DetailRow
                  label="Автопродовження"
                  value={recurring ? "Увімкнено" : "Вимкнено"}
                />
                {nextPayment && (
                  <DetailRow
                    label={recurring ? "Наступний платіж" : "Доступ до"}
                    value={formatKyivDate(nextPayment)}
                  />
                )}
                {latestPayment?.order_id && (
                  <DetailRow
                    label="Номер замовлення"
                    value={
                      <span className="break-all font-mono text-[11px] font-medium text-muted">
                        {latestPayment.order_id}
                      </span>
                    }
                  />
                )}
              </div>

              {!latestPayment && !cardMask && (
                <p className="mt-4 rounded-xl bg-surface px-3 py-2.5 text-[12px] text-muted">
                  Деталі платежу з’являться за кілька секунд після підтвердження від LiqPay.
                  Можна оновити сторінку або відкрити кабінет.
                </p>
              )}
            </>
          )}

          <div className="mt-7 flex flex-col gap-2.5 sm:flex-row sm:items-center">
            <CtaLink
              href="/app/dashboard"
              variant="emerald"
              size="lg"
              className="w-full justify-center sm:flex-1"
            >
              До кабінету
            </CtaLink>
            <Link
              href="/app/billing"
              className="inline-flex w-full items-center justify-center rounded-full border border-border bg-white px-5 py-3 text-[13px] font-semibold text-ink transition-colors hover:bg-surface sm:w-auto sm:min-w-[160px]"
            >
              Підписка
            </Link>
          </div>
        </div>

        <p className="mt-5 text-center text-[12px] text-muted">
          Квитанцію також можна переглянути в розділі «Підписка».
        </p>
      </div>
    </div>
  );
}
