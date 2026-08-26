"use client";

import { ListingCard } from "@/components/listings/ListingCard";
import {
  enrichNotificationListing,
} from "@/lib/notification-listing";
import type { Listing, Notification } from "@/types/api";
import { cn, timeAgo } from "@/lib/utils";

type Props = {
  notification: Notification & { listing: Listing };
  onOpen: () => void;
  isFavorite: boolean;
  favoriteLoading: boolean;
  onToggleFavorite: () => void;
  className?: string;
};

/** Картка сповіщення про зниження — той самий ListingCard, що в моніторингу. */
export function PriceDropNotificationCard({
  notification,
  onOpen,
  isFavorite,
  favoriteLoading,
  onToggleFavorite,
  className,
}: Props) {
  const listing = enrichNotificationListing(notification) ?? notification.listing;

  return (
    <div className={cn("relative", className)}>
      <div className="mb-1.5 flex flex-wrap items-center gap-2 px-1 text-[11px] text-muted lg:mb-2 lg:text-[13px]">
        <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-rose-700">
          Зниження ціни
        </span>
        {notification.sent_telegram ? (
          <span className="rounded-full border border-border bg-white px-2 py-0.5 font-medium">
            Telegram
          </span>
        ) : null}
        <span>{timeAgo(notification.created_at)}</span>
      </div>
      <ListingCard
        listing={listing}
        onClick={onOpen}
        isFavorite={isFavorite}
        favoriteLoading={favoriteLoading}
        onToggleFavorite={onToggleFavorite}
      />
    </div>
  );
}
