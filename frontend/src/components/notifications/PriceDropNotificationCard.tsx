"use client";

import { ListingCard } from "@/components/listings/ListingCard";
import { formatDropPercent } from "@/lib/listing-price-drop";
import {
  enrichNotificationListing,
  notificationDropPercent,
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

export function PriceDropNotificationCard({
  notification,
  onOpen,
  isFavorite,
  favoriteLoading,
  onToggleFavorite,
  className,
}: Props) {
  const listing = enrichNotificationListing(notification) ?? notification.listing;
  const dropPercent = notificationDropPercent(notification);

  return (
    <div className={cn("overflow-hidden rounded-2xl border border-rose-200/80 bg-white shadow-sm", className)}>
      <div className="flex flex-wrap items-center gap-2 border-b border-rose-100 bg-gradient-to-r from-rose-50 to-orange-50/60 px-4 py-3">
        <span className="text-[15px]" aria-hidden>
          📉
        </span>
        <div className="min-w-0 flex-1 text-[13px] font-bold text-rose-900">Зниження ціни</div>
        {dropPercent ? (
          <span className="rounded-full bg-rose-600 px-2.5 py-1 text-[11px] font-bold text-white">
            −{formatDropPercent(dropPercent)}%
          </span>
        ) : null}
        <div className="flex w-full flex-wrap items-center gap-2 text-[11px] text-rose-800/70 sm:ml-auto sm:w-auto">
          {notification.sent_telegram ? (
            <span className="rounded-full border border-rose-200 bg-white/80 px-2 py-0.5 font-medium">
              Telegram
            </span>
          ) : null}
          <span>{timeAgo(notification.created_at)}</span>
        </div>
      </div>

      <div className="p-1">
        <ListingCard
          listing={listing}
          onClick={onOpen}
          isFavorite={isFavorite}
          favoriteLoading={favoriteLoading}
          onToggleFavorite={onToggleFavorite}
          hidePriceDrop
          className="border-0 shadow-none"
        />
      </div>
    </div>
  );
}
