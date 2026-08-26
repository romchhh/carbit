import type { Listing, Notification } from "@/types/api";
import { formatDropPercent } from "@/lib/listing-price-drop";

export function enrichNotificationListing(notification: Notification): Listing | null {
  const listing = notification.listing;
  if (!listing) return null;
  if (notification.type !== "price_drop") return listing;

  const payload = notification.payload ?? {};
  const oldPrice = Number(payload.old_price) || 0;
  const dropPercent = Number(payload.drop_percent) || Number(listing.price_drop_percent) || 0;
  if (oldPrice <= 0 || dropPercent <= 0) return listing;

  return {
    ...listing,
    previous_price: oldPrice,
    price_drop_percent: dropPercent,
    price_dropped_at:
      (typeof payload.dropped_at === "string" && payload.dropped_at) ||
      listing.price_dropped_at ||
      notification.created_at,
  };
}

export function notificationDropPercent(notification: Notification): number | null {
  if (notification.type !== "price_drop") return null;
  const fromPayload = Number(notification.payload?.drop_percent);
  if (fromPayload > 0) return fromPayload;
  const fromListing = Number(notification.listing?.price_drop_percent);
  return fromListing > 0 ? fromListing : null;
}

export function notificationDropLabel(notification: Notification): string | null {
  const percent = notificationDropPercent(notification);
  if (!percent) return notification.body || null;
  return `Ціну знижено на ${formatDropPercent(percent)}%`;
}
