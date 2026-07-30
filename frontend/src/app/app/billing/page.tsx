"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { billing as billingApi, ApiError } from "@/lib/api";
import type { Plan, Subscription } from "@/types/api";
import { useAuth } from "@/contexts/AuthProvider";
import { IconZap } from "@/components/icons";
import { AppPage, AppSection } from "@/components/layout/AppPage";
import { LiqPayLogo } from "@/components/brand/LiqPayLogo";
import { CancelRenewalDialog } from "@/components/billing/CancelRenewalDialog";
import { PricingPlans, type PricingCardModel } from "@/components/pricing/PricingPlans";
import { PRICING_PLANS } from "@/lib/pricing-plans";
import { submitLiqPayCheckout } from "@/lib/liqpay-checkout";

function formatPrice(uah: number): string {
  if (uah <= 0) return "0";
  return uah.toLocaleString("uk-UA");
}

function toCabinetCards(
  apiPlans: Plan[],
  opts: {
    currentPlanId: string | undefined;
    loadingId: string | null;
    liqpayEnabled: boolean;
  },
): PricingCardModel[] {
  const { currentPlanId, loadingId, liqpayEnabled } = opts;
  return apiPlans.map(api => {
    const meta = PRICING_PLANS.find(p => p.id === api.id);
    const current = currentPlanId === api.id;
    const isFree = api.id === "free";
    return {
      id: api.id,
      name: meta?.name ?? api.name,
      description: meta?.description ?? api.description,
      price: formatPrice(api.price_uah),
      period: meta?.period ?? (api.price_uah > 0 ? "грн / 30 днів" : "7 днів"),
      features: meta?.features?.length ? meta.features : api.features,
      missing: meta?.missing ?? [],
      accent: meta?.accent ?? false,
      popular: meta?.popular ?? false,
      current,
      loading: loadingId === api.id,
      disabled: current || loadingId === api.id,
      cta: current
        ? "Ваш тариф"
        : isFree
          ? "Перейти на Free"
          : liqpayEnabled
            ? "Оплатити LiqPay"
            : "Оплатити",
    };
  });
}

function BillingPageInner() {
  const { user, refreshUser } = useAuth();
  const searchParams = useSearchParams();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [cancelError, setCancelError] = useState("");

  const load = async () => {
    const [nextPlans, nextSub] = await Promise.all([
      billingApi.plans(),
      billingApi.subscription().catch(() => null),
    ]);
    setPlans(nextPlans);
    if (nextSub) setSubscription(nextSub);
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (searchParams.get("paid") !== "1") return;
    // Старий result_url LiqPay — ведемо на нову сторінку успіху.
    window.location.replace("/app/billing/success");
  }, [searchParams]);

  const liqpayEnabled = Boolean(subscription?.liqpay_enabled);
  const currentPlanId = subscription?.plan ?? user?.plan;
  const canCancelRenewal =
    Boolean(subscription) &&
    subscription?.plan !== "free" &&
    Boolean(subscription?.recurring_active);

  const cards = useMemo(
    () =>
      toCabinetCards(plans, {
        currentPlanId,
        loadingId: loading,
        liqpayEnabled,
      }),
    [plans, currentPlanId, loading, liqpayEnabled],
  );

  const orderPlan = async (planId: string) => {
    if (planId === currentPlanId) return;
    setLoading(planId);
    setError("");
    setSuccess("");
    try {
      if (planId === "free") {
        const sub = await billingApi.subscribe("free");
        setSubscription(sub);
        await refreshUser();
        setSuccess("Перейшли на безкоштовний план. Рекурентні списання скасовано.");
        return;
      }

      // Платні плани — лише через LiqPay Checkout (не через /subscribe).
      // apply_credit: при апгрейді з оплаченого тарифу — доплата з урахуванням залишку днів.
      const checkout = await billingApi.checkout(planId, true);
      if (checkout.free_upgrade) {
        await refreshUser();
        window.location.href = "/app/billing/success";
        return;
      }
      if (checkout.credit_uah && checkout.credit_uah > 0) {
        setSuccess(
          `Зараховано залишок ${checkout.credit_uah} грн. До сплати ${checkout.amount} грн` +
            (checkout.enable_subscribe === false
              ? ". Автопродовження увімкніть пізніше за повною ціною."
              : "."),
        );
      }
      submitLiqPayCheckout(checkout.checkout_url, checkout.data, checkout.signature);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Помилка оплати";
      if (err instanceof ApiError && (err.status === 503 || /не налаштовано|не підключен/i.test(msg))) {
        setError(
          "LiqPay не налаштовано на сервері. Додайте LIQPAY_PUBLIC_KEY і LIQPAY_PRIVATE_KEY у .env і перезапустіть backend.",
        );
      } else {
        setError(msg);
      }
      setLoading(null);
    }
  };

  const confirmCancelRenewal = async (payload: { reason: string; note: string }) => {
    setCancelLoading(true);
    setCancelError("");
    try {
      const sub = await billingApi.unsubscribe({
        reason: payload.reason,
        note: payload.note || undefined,
      });
      setSubscription(sub);
      await refreshUser();
      setCancelOpen(false);
      setSuccess(
        "Автопродовження скасовано. Доступ збережеться до кінця оплаченого періоду.",
      );
    } catch (err) {
      setCancelError(
        err instanceof ApiError ? err.message : "Не вдалося скасувати підписку",
      );
    } finally {
      setCancelLoading(false);
    }
  };

  return (
    <AppPage wide title="Підписка" description="Тарифи Carbit — моніторинг AUTO.RIA, OLX і Telegram" tourId="tour-section-billing">
      {subscription?.is_trial_active && (
        <AppSection className="mb-5 flex items-center gap-3 !border-emerald/20 !bg-emerald-light/30">
          <IconZap size={18} className="shrink-0 text-emerald-dark" />
          <div>
            <div className="text-[14px] font-semibold text-ink">Trial активний</div>
            <div className="text-[12px] text-muted">
              Після trial оберіть платний тариф — ліміт пошуків зросте, сповіщення лишаться в Telegram
            </div>
          </div>
        </AppSection>
      )}

      <div className="mb-6 rounded-2xl border border-border/60 bg-surface/50 px-4 py-4 sm:px-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted">Зараз</div>
            <div className="mt-1 text-[18px] font-black text-ink">
              {subscription?.plan_name ?? user?.plan ?? "—"}
              {subscription?.is_trial_active ? (
                <span className="ml-2 text-[12px] font-semibold text-emerald-dark">Trial</span>
              ) : null}
            </div>
            <p className="mt-1 max-w-lg text-[13px] text-muted">
              До {subscription?.searches_limit ?? user?.searches_limit ?? "—"} активних моніторингів.
              Оплата раз на 30 днів через LiqPay; при апгрейді залишок днів поточного тарифу
              зараховується в доплату.
            </p>
          </div>
          {subscription?.plan_expires_at && subscription.plan !== "free" && (
            <div className="rounded-xl bg-white px-3 py-2 text-right shadow-sm">
              <div className="text-[11px] text-muted">Діє до</div>
              <div className="text-[13px] font-semibold text-ink">
                {new Date(subscription.plan_expires_at).toLocaleDateString("uk-UA")}
              </div>
            </div>
          )}
        </div>
        <ul className="mt-4 grid gap-2 text-[12px] text-muted sm:grid-cols-3">
          <li className="rounded-lg bg-white/80 px-3 py-2">✓ AUTO.RIA + OLX в одному кабінеті</li>
          <li className="rounded-lg bg-white/80 px-3 py-2">✓ Миттєві сповіщення в Telegram</li>
          <li className="rounded-lg bg-white/80 px-3 py-2">✓ Скасування автопродовження в кабінеті</li>
        </ul>
      </div>

      {success && (
        <p className="mb-4 rounded-xl border border-emerald/25 bg-emerald-light/40 px-3 py-2 text-[13px] text-emerald-dark">
          {success}
        </p>
      )}
      {error && (
        <p className="mb-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
      )}

      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h2 className="text-[16px] font-bold text-ink">Оберіть тариф</h2>
          <p className="mt-0.5 text-[12px] text-muted">Натисніть картку — відкриється безпечна оплата LiqPay</p>
        </div>
        <Link href="/pricing" className="shrink-0 text-[12px] font-semibold text-emerald-dark hover:underline">
          Порівняльна таблиця →
        </Link>
      </div>

      <div className="pt-1">
        <PricingPlans variant="cabinet" plans={cards} onSelect={id => void orderPlan(id)} />
      </div>

      <div className="mt-8 flex flex-col items-center gap-3 text-center">
        <LiqPayLogo height={28} />
        <p className="max-w-md text-[12px] text-muted">
          Оплата карткою Visa/Mastercard через захищений Checkout LiqPay. Рекурентна підписка — щомісяця.
          {!liqpayEnabled && (
            <>
              {" "}
              Якщо оплата не відкривається — перевірте ключі LiqPay у{" "}
              <Link href="/payment" className="text-emerald-dark underline">
                Оплата і повернення
              </Link>
              .
            </>
          )}
        </p>
      </div>

      {canCancelRenewal && (
        <div className="mt-10 border-t border-border/50 pt-6 text-center">
          <button
            type="button"
            onClick={() => {
              setCancelError("");
              setCancelOpen(true);
            }}
            className="text-[11px] text-muted/80 underline-offset-2 transition hover:text-muted hover:underline"
          >
            Cancel subscription
          </button>
          <p className="mx-auto mt-1.5 max-w-sm text-[10px] leading-relaxed text-muted/60">
            Скасує автопродовження. Доступ лишиться до кінця оплаченого періоду.
          </p>
        </div>
      )}

      <CancelRenewalDialog
        open={cancelOpen}
        expiresAt={subscription?.plan_expires_at}
        loading={cancelLoading}
        error={cancelError}
        onClose={() => {
          if (!cancelLoading) setCancelOpen(false);
        }}
        onConfirm={payload => void confirmCancelRenewal(payload)}
      />
    </AppPage>
  );
}

export default function BillingPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
        </div>
      }
    >
      <BillingPageInner />
    </Suspense>
  );
}
