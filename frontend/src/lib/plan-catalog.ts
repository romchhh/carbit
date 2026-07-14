import { PRICING_PLANS, type PricingPlan } from "@/lib/pricing-plans";

export const PAID_PLAN_ORDER = ["lite", "standard", "pro"] as const;

export function getPricingPlan(planId: string): PricingPlan | undefined {
  return PRICING_PLANS.find(p => p.id === planId);
}

export function planDisplayName(planId: string): string {
  return getPricingPlan(planId)?.name ?? planId;
}

/** Ціна для відображення без пробілів-тисячних (для коротких CTA). */
export function planPriceNumber(planId: string): number {
  const raw = getPricingPlan(planId)?.price ?? "0";
  return Number(String(raw).replace(/\s/g, "")) || 0;
}

export function formatPlanPrice(planId: string): string {
  const n = planPriceNumber(planId);
  if (n <= 0) return "0 грн";
  return `${n.toLocaleString("uk-UA")} грн`;
}

/** Наступний платний план з більшим лімітом. */
export function nextPaidPlanId(currentPlanId: string, currentLimit: number): string | null {
  const order = ["free", ...PAID_PLAN_ORDER];
  const curIdx = order.indexOf(currentPlanId);
  for (const id of PAID_PLAN_ORDER) {
    if (id === currentPlanId) continue;
    const nextIdx = order.indexOf(id);
    if (nextIdx <= curIdx && currentPlanId !== "free") continue;
    if (planMonitorLimit(id) > currentLimit) return id;
  }
  return null;
}

export function planMonitorLimit(planId: string): number {
  const map: Record<string, number> = { free: 1, lite: 10, standard: 30, pro: 100 };
  return map[planId] ?? 1;
}
