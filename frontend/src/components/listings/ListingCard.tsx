"use client";

import Image from "next/image";
import { Badge } from "@/components/ui/Badge";
import { IconArrowRight } from "@/components/icons";
import { ListingFavoriteButton } from "@/components/listings/ListingFavoriteButton";
import { VinCheckButton } from "@/components/listings/VinCheckButton";
import { getAutoRiaHighlights } from "@/lib/auto-ria-details";
import { hasVinCheck } from "@/lib/vin-check";
import { cn } from "@/lib/utils";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing;
  onClick: () => void;
  className?: string;
  isFavorite?: boolean;
  favoriteLoading?: boolean;
  onToggleFavorite?: () => void;
};

function shortRegion(region: string) {
  const city = region.split(",")[0]?.trim();
  return city || region;
}

export function ListingCard({
  listing,
  onClick,
  className,
  isFavorite = false,
  favoriteLoading = false,
  onToggleFavorite,
}: Props) {
  const images = Array.isArray(listing.images) ? listing.images : [];
  const price = Number(listing.price) || 0;
  const fuel = typeof listing.fuel === "string" ? listing.fuel : "";
  const region = typeof listing.region === "string" ? listing.region : "";
  const sellerLabel = listing.seller_type === "dealer" ? "Автосалон" : "Приват";
  const showVinBlock = Boolean(listing.vin) || hasVinCheck(listing);
  const highlights = getAutoRiaHighlights(listing.source_data).slice(0, 3);

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={e => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className={cn(
        "group cursor-pointer overflow-hidden rounded-2xl border border-border/80 bg-white text-left shadow-[0_2px_12px_-6px_rgba(10,12,14,0.12)] transition-all",
        "hover:border-emerald/30 hover:shadow-[0_8px_24px_-10px_rgba(10,12,14,0.16)]",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald/40",
        "sm:flex sm:gap-4 sm:p-4",
        className,
      )}
    >
      {/* Mobile: full-width photo on top */}
      <div className="relative aspect-[16/10] w-full bg-surface sm:hidden">
        {images[0] ? (
          <Image
            src={images[0]}
            alt={listing.title}
            fill
            className="object-cover"
            sizes="100vw"
            unoptimized
          />
        ) : (
          <div className="flex h-full items-center justify-center text-[13px] text-muted">
            Без фото
          </div>
        )}
        <div className="absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-3">
          <Badge variant="gray" className="bg-white/95 text-[10px] shadow-sm">
            AUTO.RIA
          </Badge>
          <div className="flex items-center gap-2">
            {onToggleFavorite && (
              <ListingFavoriteButton
                active={isFavorite}
                loading={favoriteLoading}
                onToggle={onToggleFavorite}
              />
            )}
            <span className="rounded-full bg-ink/75 px-2.5 py-1 text-[10px] font-medium text-white">
              {sellerLabel}
            </span>
          </div>
        </div>
      </div>

      {/* Desktop: thumbnail left */}
      <div className="relative hidden h-36 w-52 shrink-0 overflow-hidden rounded-xl bg-surface sm:block">
        {images[0] ? (
          <Image
            src={images[0]}
            alt={listing.title}
            fill
            className="object-cover transition-transform duration-300 group-hover:scale-[1.02]"
            sizes="208px"
            unoptimized
          />
        ) : (
          <div className="flex h-full items-center justify-center text-[13px] text-muted">
            Без фото
          </div>
        )}
        {onToggleFavorite && (
          <div className="absolute right-2 top-2">
            <ListingFavoriteButton
              active={isFavorite}
              loading={favoriteLoading}
              onToggle={onToggleFavorite}
            />
          </div>
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col p-4 pt-3.5 sm:p-0">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-2 text-[16px] font-bold leading-snug text-ink sm:text-[15px] sm:line-clamp-1">
              {listing.title}
            </h3>
            <p className="mt-2 text-[22px] font-black leading-none tracking-tight text-ink sm:hidden">
              {price.toLocaleString("uk-UA")}
              <span className="ml-1 text-[13px] font-semibold text-muted">грн</span>
            </p>
          </div>
          <div className="hidden shrink-0 text-right sm:block">
            <div className="text-[20px] font-black leading-none text-ink">
              {price.toLocaleString("uk-UA")}
            </div>
            <div className="text-[11px] text-muted">грн</div>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5 sm:mt-2">
          {listing.year > 0 && (
            <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
              {listing.year}
            </span>
          )}
          {listing.mileage > 0 && (
            <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
              {listing.mileage.toLocaleString("uk-UA")} км
            </span>
          )}
          {listing.transmission && (
            <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
              {listing.transmission}
            </span>
          )}
          {fuel && (
            <span className="max-w-full truncate rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
              {fuel.split(",")[0]?.trim()}
            </span>
          )}
          {highlights.map((item, index) => (
            <span
              key={`${item}-${index}`}
              className="max-w-full truncate rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink"
            >
              {item}
            </span>
          ))}
        </div>

        {showVinBlock && (
          <div
            className="mt-3 flex flex-wrap items-center gap-2"
            onClick={e => e.stopPropagation()}
            onKeyDown={e => e.stopPropagation()}
          >
            {listing.vin && (
              <span className="rounded-full bg-surface px-2.5 py-1 font-mono text-[11px] font-medium tracking-wide text-ink">
                VIN: {listing.vin}
              </span>
            )}
            {listing.vin_checked && (
              <Badge variant="emerald" className="text-[10px]">
                VIN перевірено
              </Badge>
            )}
            <VinCheckButton listing={listing} />
          </div>
        )}

        <div className="mt-3 flex items-center gap-2 border-t border-border/60 pt-3 sm:mt-auto sm:border-0 sm:pt-2.5">
          <span className="min-w-0 flex-1 truncate text-[12px] text-muted">
            {shortRegion(region)}
          </span>
          <span className="hidden items-center gap-1.5 sm:flex">
            <Badge variant="outline" className="text-[10px]">AUTO.RIA</Badge>
            <span className="text-[11px] text-muted">{sellerLabel}</span>
          </span>
          <span className="flex items-center gap-0.5 text-[12px] font-semibold text-emerald-dark sm:ml-auto">
            Деталі
            <IconArrowRight
              size={12}
              className="transition-transform group-hover:translate-x-0.5"
            />
          </span>
        </div>
      </div>
    </article>
  );
}
