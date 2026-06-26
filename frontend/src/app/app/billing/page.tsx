"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { billing as billingApi, ApiError } from "@/lib/api";
import type { Plan, Subscription } from "@/types/api";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { IconZap, IconCheck } from "@/components/icons";
import { AppPage, AppSection } from "@/components/layout/AppPage";

export default function BillingPage() {
  const { user, refreshUser } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    billingApi.plans().then(setPlans);
    billingApi.subscription().then(setSubscription).catch(() => {});
  }, []);

  const subscribe = async (planId: string) => {
    setLoading(planId);
    setError("");
    try {
      const sub = await billingApi.subscribe(planId);
      setSubscription(sub);
      await refreshUser();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Помилка");
    } finally {
      setLoading(null);
    }
  };

  return (
    <AppPage wide title="Підписка" description="Оберіть тариф під ваші задачі">
      {subscription?.is_trial_active && (
        <AppSection className="mb-5 flex items-center gap-3 !border-emerald/20 !bg-emerald-light/30">
          <IconZap size={18} className="shrink-0 text-emerald-dark" />
          <div>
            <div className="text-[14px] font-semibold text-ink">Trial активний</div>
            <div className="text-[12px] text-muted">3 дні безкоштовного доступу</div>
          </div>
        </AppSection>
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
                <Button variant="primary" size="sm" className="w-full" loading={loading === plan.id} onClick={() => subscribe(plan.id)}>
                  Обрати
                </Button>
              )}
            </AppSection>
          );
        })}
      </div>

      <p className="mt-6 text-center text-[12px] text-muted">
        Оплата через LiqPay / Mono Pay — незабаром
      </p>
    </AppPage>
  );
}
