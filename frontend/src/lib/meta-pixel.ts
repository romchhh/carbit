import { FACEBOOK_PIXEL_ID } from "@/components/analytics/FacebookPixel";

export { FACEBOOK_PIXEL_ID };

declare global {
  interface Window {
    fbq?: (...args: unknown[]) => void;
  }
}

export function buildMetaPurchaseEventId(orderId: string, paymentId?: string | null): string {
  if (paymentId) return `purchase_${paymentId}`;
  return `purchase_${orderId}`;
}

export function trackMetaPurchase(params: {
  value: number;
  currency?: string;
  contentName?: string;
  contentIds?: string[];
  orderId: string;
  paymentId?: string | null;
}): void {
  if (typeof window === "undefined" || typeof window.fbq !== "function") return;
  const eventId = buildMetaPurchaseEventId(params.orderId, params.paymentId);
  window.fbq(
    "track",
    "Purchase",
    {
      value: params.value,
      currency: (params.currency || "UAH").toUpperCase(),
      content_name: params.contentName,
      content_ids: params.contentIds,
      content_type: "product",
    },
    { eventID: eventId },
  );
}
