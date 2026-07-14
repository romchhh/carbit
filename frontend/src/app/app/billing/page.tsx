"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { billing as billingApi, ApiError } from "@/lib/api";
import type { Plan, Subscription } from "@/types/api";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { IconZap, IconCheck } from "@/components/icons";
import { AppPage, AppSection } from "@/components/layout/AppPage";
import { LiqPayLogo } from "@/components/brand/LiqPayLogo";

function submitLiqPayCheckout(checkoutUrl: string, data: string, signature: string) {
  // Повний form POST — не відкривати старе checkout-посилання в новій вкладці
  // (сесія короткоживуча → часто 403 Forbidden на /checkout/card/...).
  const form = document.createElement("form");
  form.method = "POST";
  form.action = checkoutUrl;
  form.acceptCharset = "utf-8";
  form.style.display = "none";

  const dataInput = document.createElement("input");
  dataInput.type = "hidden";
  dataInput.name = "data";
  dataInput.value = data;
  form.appendChild(dataInput);

  const signInput = document.createElement("input");
  signInput.type = "hidden";
  signInput.name = "signature";
  signInput.value = signature;
  form.appendChild(signInput);

  document.body.appendChild(form);
  form.submit();
}

function BillingPageInner() {
  const { user, refreshUser } = useAuth();
  const searchParams = useSearchParams();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

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
    setSuccess("Оплату прийнято. Якщо тариф ще не оновився — зачекайте кілька секунд і оновіть сторінку.");
    void (async () => {
      await refreshUser();
      await load();
    })();
  }, [searchParams, refreshUser]);

  const liqpayEnabled = Boolean(subscription?.liqpay_enabled);

  const orderPlan = async (planId: string) => {
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
      const checkout = await billingApi.checkout(planId);
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

  const cancelRecurring = async () => {
    setLoading("unsubscribe");
    setError("");
    try {
      const sub = await billingApi.unsubscribe();
      setSubscription(sub);
      await refreshUser();
      setSuccess("Автопродовження скасовано. Доступ збережеться до кінця оплаченого періоду.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося скасувати підписку");
    } finally {
      setLoading(null);
    }
  };

  return (
    <AppPage wide title="Підписка" description="Оберіть тариф під ваші задачі" tourId="tour-section-billing">
      {subscription?.is_trial_active && (
        <AppSection className="mb-5 flex items-center gap-3 !border-emerald/20 !bg-emerald-light/30">
          <IconZap size={18} className="shrink-0 text-emerald-dark" />
          <div>
            <div className="text-[14px] font-semibold text-ink">Trial активний</div>
            <div className="text-[12px] text-muted">3 дні безкоштовного доступу</div>
          </div>
        </AppSection>
      )}

      {success && (
        <p className="mb-4 rounded-xl border border-emerald/25 bg-emerald-light/40 px-3 py-2 text-[13px] text-emerald-dark">
          {success}
        </p>
      )}
      {error && (
        <p className="mb-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {plans.map(plan => {
          const isCurrent = subscription?.plan === plan.id || user?.plan === plan.id;
          return (
            <AppSection
              key={plan.id}
              className={cn("flex flex-col !bg-white", isCurrent && "!border-emerald/40 ring-2 ring-emerald/15")}
            >
              <div className="mb-4">
                {isCurrent && <Badge variant="emerald" className="mb-2">Поточний</Badge>}
                <div className="text-[17px] font-black text-ink">{plan.name}</div>
                <div className="mt-0.5 text-[12px] text-muted">{plan.description}</div>
              </div>
              <div className="mb-1 text-[26px] font-black text-ink">
                {plan.price_uah === 0 ? "0" : plan.price_uah.toLocaleString("uk-UA")}
                {plan.price_uah > 0 && <span className="text-[13px] font-medium text-muted"> грн/міс</span>}
              </div>
              <ul className="my-4 flex-1 space-y-1.5">
                {plan.features.map(f => (
                  <li key={f} className="flex items-start gap-1.5 text-[12px] text-muted">
                    <IconCheck size={12} className="mt-0.5 shrink-0 text-emerald" />{f}
                  </li>
                ))}
              </ul>
              {!isCurrent && plan.id !== "free" && (
                <Button
                  variant="primary"
                  size="sm"
                  className="w-full"
                  loading={loading === plan.id}
                  onClick={() => void orderPlan(plan.id)}
                >
                  {liqpayEnabled ? "Оплатити LiqPay" : "Оплатити"}
                </Button>
              )}
              {!isCurrent && plan.id === "free" && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full"
                  loading={loading === plan.id}
                  onClick={() => void orderPlan("free")}
                >
                  Перейти на Free
                </Button>
              )}
            </AppSection>
          );
        })}
      </div>

      {subscription && subscription.plan !== "free" && (
        <div className="mt-5 flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[12px] text-muted">
            Автопродовження через LiqPay. Можна скасувати — доступ лишиться до{" "}
            {subscription.plan_expires_at
              ? new Date(subscription.plan_expires_at).toLocaleDateString("uk-UA")
              : "кінця періоду"}
            .
          </p>
          <Button
            variant="secondary"
            size="sm"
            loading={loading === "unsubscribe"}
            onClick={() => void cancelRecurring()}
          >
            Скасувати автопродовження
          </Button>
        </div>
      )}

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
