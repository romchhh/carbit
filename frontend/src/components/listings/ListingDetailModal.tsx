"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { IconGlobe, IconHeart, IconX } from "@/components/icons";
import { AutoRiaListingDetails } from "@/components/listings/AutoRiaListingDetails";
import { SourceBadge } from "@/components/listings/SourceBadge";
import { PublishedTimeBadge } from "@/components/listings/PublishedTimeBadge";
import { VinCheckButton } from "@/components/listings/VinCheckButton";
import { getAutoRiaHighlights } from "@/lib/auto-ria-details";
import {
  listingAttributionUrl,
  listingOpenLabel,
  listingSourceSiteName,
} from "@/lib/listing-source";
import { hasVinCheck } from "@/lib/vin-check";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";
import { cn, formatMileage, publishedAgoLabel } from "@/lib/utils";
import { formatListingPrice, resolveDisplayCurrency } from "@/lib/display-currency";
import { useAuth } from "@/contexts/AuthProvider";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing | null;
  onClose: () => void;
  isFavorite?: boolean;
  favoriteLoading?: boolean;
  onToggleFavorite?: () => void;
  favoriteError?: string | null;
};

const MODAL_ACTION_CLASS =
  "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-ink transition-colors hover:bg-surface active:bg-surface";

export function ListingDetailModal({
  listing,
  onClose,
  isFavorite = false,
  favoriteLoading = false,
  onToggleFavorite,
  favoriteError,
}: Props) {
  const { user } = useAuth();
  const priceLabel = listing
    ? formatListingPrice(
        listing.price,
        listing.currency,
        resolveDisplayCurrency(user?.preferred_currency),
        listing.source_data,
      )
    : "";
  const [photoIndex, setPhotoIndex] = useState(0);
  const galleryRef = useRef<HTMLDivElement>(null);
  const photoIndexRef = useRef(photoIndex);
  const dragStartY = useRef<number | null>(null);
  photoIndexRef.current = photoIndex;

  const scrollToPhoto = useCallback((index: number) => {
    const container = galleryRef.current;
    if (!container) return;

    const slide = container.children[index] as HTMLElement | undefined;
    if (!slide) return;

    container.scrollTo({ left: slide.offsetLeft, behavior: "smooth" });
    setPhotoIndex(index);
  }, []);

  const handleDragStart = useCallback((clientY: number) => {
    dragStartY.current = clientY;
  }, []);

  const handleDragEnd = useCallback(
    (clientY: number) => {
      if (dragStartY.current === null) return;
      const delta = clientY - dragStartY.current;
      dragStartY.current = null;
      if (delta > 48) onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!listing) return;
    setPhotoIndex(0);
    lockBodyScroll();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      const lastIndex = Math.max(0, listing.images.length - 1);
      if (e.key === "ArrowLeft") scrollToPhoto(Math.max(0, photoIndexRef.current - 1));
      if (e.key === "ArrowRight") scrollToPhoto(Math.min(lastIndex, photoIndexRef.current + 1));
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      unlockBodyScroll();
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [listing, onClose, scrollToPhoto]);

  useEffect(() => {
    const container = galleryRef.current;
    if (!container || !listing || listing.images.length <= 1) return;

    const slides = Array.from(container.children) as HTMLElement[];
    const observer = new IntersectionObserver(
      entries => {
        const visible = entries
          .filter(entry => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (!visible.length) return;

        const index = slides.indexOf(visible[0].target as HTMLElement);
        if (index >= 0) setPhotoIndex(index);
      },
      { root: container, threshold: 0.6 },
    );

    slides.forEach(slide => observer.observe(slide));
    return () => observer.disconnect();
  }, [listing]);

  useEffect(() => {
    if (!listing) return;
    galleryRef.current?.scrollTo({ left: 0 });
  }, [listing?.id]);

  if (!listing) return null;

  const photos = listing.images.length ? listing.images : [];
  const hasAutoRiaDetails =
    listing.source === "auto_ria" &&
    listing.source_data &&
    Object.keys(listing.source_data).length > 0;

  const highlights = hasAutoRiaDetails ? [] : getAutoRiaHighlights(listing.source_data);
  const source = listing.source_data ?? {};
  const priceUsd = typeof source.USD === "number" ? source.USD : null;
  const priceEur = typeof source.EUR === "number" ? source.EUR : null;

  const specs = hasAutoRiaDetails
    ? []
    : [
        { label: "Рік", value: listing.year ? String(listing.year) : "—" },
        { label: "Пробіг", value: listing.mileage ? formatMileage(listing.mileage) : "—" },
        { label: "Паливо", value: listing.fuel || "—" },
        { label: "КПП", value: listing.transmission || "—" },
        { label: "Регіон", value: listing.region || "—" },
        {
          label: "Продавець",
          value: listing.seller_type === "dealer" ? "Автосалон" : "Приват",
        },
        ...(listing.vin ? [{ label: "VIN", value: listing.vin }] : []),
        ...(priceUsd ? [{ label: "Ціна USD", value: priceUsd.toLocaleString("uk-UA") }] : []),
        ...(priceEur ? [{ label: "Ціна EUR", value: priceEur.toLocaleString("uk-UA") }] : []),
      ];

  return (
    <div
      className="fixed inset-0 z-[120] flex items-end justify-center p-0 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="listing-modal-title"
    >
      <button
        type="button"
        aria-label="Закрити"
        className="absolute inset-0 bg-ink/60"
        onClick={onClose}
      />

      <div className="relative z-10 flex max-h-[92dvh] w-full max-w-[880px] flex-col overflow-hidden rounded-t-[1.5rem] border border-border bg-white shadow-[0_24px_80px_-20px_rgba(10,12,14,0.35)] sm:rounded-[1.5rem]">
        <div className="z-30 shrink-0 border-b border-border/60 bg-white/95 backdrop-blur-md">
          <button
            type="button"
            aria-label="Згорнути"
            onClick={onClose}
            onTouchStart={e => handleDragStart(e.touches[0].clientY)}
            onTouchEnd={e => handleDragEnd(e.changedTouches[0].clientY)}
            onPointerDown={e => {
              if (e.pointerType === "mouse") handleDragStart(e.clientY);
            }}
            onPointerUp={e => {
              if (e.pointerType === "mouse") handleDragEnd(e.clientY);
            }}
            className="flex w-full touch-none justify-center px-4 pb-1 pt-2.5 sm:hidden"
          >
            <span className="h-1 w-10 rounded-full bg-border" />
          </button>

          <div className="flex items-center gap-3 px-3 pb-2.5 sm:px-4 sm:pb-3">
            <div className="min-w-0 flex-1 sm:hidden">
              <SourceBadge source={listing.source} className="mb-1 bg-transparent px-0 shadow-none" />
              <h2 className="truncate text-[15px] font-bold leading-snug text-ink">
                {listing.title}
              </h2>
            </div>
            <div className="hidden min-w-0 flex-1 sm:block">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">Деталі авто</p>
              <p className="truncate text-[15px] font-bold leading-snug text-ink">{listing.title}</p>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {onToggleFavorite && (
                <button
                  type="button"
                  aria-label={isFavorite ? "Прибрати з обраного" : "Додати в обране"}
                  aria-pressed={isFavorite}
                  disabled={favoriteLoading}
                  onClick={onToggleFavorite}
                  className={cn(
                    MODAL_ACTION_CLASS,
                    isFavorite ? "text-emerald" : "text-muted hover:text-emerald-dark",
                    favoriteLoading && "opacity-60",
                  )}
                >
                  <IconHeart size={18} className={cn(isFavorite && "fill-current")} />
                </button>
              )}
              <button type="button" aria-label="Закрити" onClick={onClose} className={MODAL_ACTION_CLASS}>
                <IconX size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
          {/* Mobile gallery */}
          <div className="relative aspect-[16/10] w-full bg-surface sm:hidden">
            {photos.length > 0 ? (
              <div
                ref={galleryRef}
                className="flex h-full w-full snap-x snap-mandatory overflow-x-auto scroll-smooth scrollbar-hide touch-pan-x"
              >
                {photos.map((src, index) => (
                  <div
                    key={`${src}-${index}`}
                    className="relative h-full w-full shrink-0 snap-start snap-always"
                  >
                    <Image
                      src={src}
                      alt={`${listing.title} — фото ${index + 1}`}
                      fill
                      className="object-cover"
                      sizes="100vw"
                      unoptimized
                      priority={index === 0}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-[13px] text-muted">
                Фото відсутнє
              </div>
            )}

            {photos.length > 1 && (
              <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/50 px-2.5 py-1 text-[11px] font-semibold tabular-nums text-white backdrop-blur-sm">
                {photoIndex + 1} / {photos.length}
              </div>
            )}
            <div className="pointer-events-none absolute bottom-3 left-3">
              <PublishedTimeBadge date={listing.published_at} short />
            </div>
          </div>

          {photos.length > 1 && (
            <div className="flex gap-2 overflow-x-auto border-b border-border px-4 py-3 scrollbar-hide sm:hidden">
              {photos.map((src, index) => (
                <button
                  key={`${src}-${index}-thumb-mobile`}
                  type="button"
                  onClick={() => scrollToPhoto(index)}
                  className={cn(
                    "relative h-14 w-20 shrink-0 overflow-hidden rounded-lg border-2 transition-colors",
                    index === photoIndex ? "border-emerald" : "border-transparent opacity-70 hover:opacity-100",
                  )}
                >
                  <Image src={src} alt="" fill className="object-cover" sizes="80px" unoptimized />
                </button>
              ))}
            </div>
          )}

          {/* Desktop: photo left, summary right */}
          <div className="hidden border-b border-border/60 sm:block">
            <div className="flex gap-5 p-5">
              <div className="w-1/2 min-w-0">
                <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-surface">
                  {photos.length > 0 ? (
                    <Image
                      src={photos[photoIndex] ?? photos[0]}
                      alt={listing.title}
                      fill
                      className="object-cover"
                      sizes="50vw"
                      unoptimized
                      priority
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-[13px] text-muted">
                      Фото відсутнє
                    </div>
                  )}
                  {photos.length > 1 && (
                    <div className="absolute bottom-2 right-2 rounded-full bg-black/55 px-2 py-0.5 text-[10px] font-semibold text-white">
                      {photoIndex + 1} / {photos.length}
                    </div>
                  )}
                  <div className="absolute bottom-2 left-2">
                    <PublishedTimeBadge date={listing.published_at} short />
                  </div>
                </div>

                {photos.length > 1 && (
                  <div className="mt-2.5 flex gap-1.5 overflow-x-auto scrollbar-hide">
                    {photos.map((src, index) => (
                      <button
                        key={`${src}-${index}-thumb-desktop`}
                        type="button"
                        onClick={() => setPhotoIndex(index)}
                        className={cn(
                          "relative h-12 w-16 shrink-0 overflow-hidden rounded-lg border-2 transition-colors",
                          index === photoIndex
                            ? "border-emerald"
                            : "border-transparent opacity-70 hover:opacity-100",
                        )}
                      >
                        <Image src={src} alt="" fill className="object-cover" sizes="64px" unoptimized />
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="w-1/2 min-w-0">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <SourceBadge source={listing.source} variant="outline" className="mb-2" />
                    <h2 id="listing-modal-title" className="text-[20px] font-bold leading-snug text-ink">
                      {listing.title}
                    </h2>
                    <p className="mt-1 text-[13px] text-muted">
                      {listing.brand} {listing.model}
                    </p>
                    {publishedAgoLabel(listing.published_at) && (
                      <p className="mt-1 text-[12px] text-muted/80">
                        {publishedAgoLabel(listing.published_at)}
                      </p>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="text-[26px] font-black leading-none text-ink">
                      {priceLabel}
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-1.5">
                  {listing.year > 0 && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {listing.year}
                    </span>
                  )}
                  {listing.mileage > 0 && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {formatMileage(listing.mileage)}
                    </span>
                  )}
                  {listing.transmission && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {listing.transmission}
                    </span>
                  )}
                  {listing.fuel && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {listing.fuel.split(",")[0]?.trim()}
                    </span>
                  )}
                  {listing.region && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {listing.region.split(",")[0]?.trim()}
                    </span>
                  )}
                  <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                    {listing.seller_type === "dealer" ? "Автосалон" : "Приват"}
                  </span>
                </div>

                {highlights.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {highlights.map((item, index) => (
                      <span
                        key={`${item}-${index}`}
                        className="rounded-full bg-emerald-light/50 px-2.5 py-1 text-[11px] font-medium text-emerald-dark"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-5 px-4 py-5 sm:px-6 sm:py-6">
            {/* Mobile-only price block (desktop shows it in top row) */}
            <div className="flex flex-wrap items-end justify-between gap-3 sm:hidden">
              <div>
                <div className="text-[28px] font-black leading-none text-ink">
                  {priceLabel}
                </div>
                <p className="mt-1.5 text-[12px] text-muted">
                  {listing.brand} {listing.model}
                </p>
                {publishedAgoLabel(listing.published_at) && (
                  <p className="mt-1 text-[12px] text-muted/80">
                    {publishedAgoLabel(listing.published_at)}
                  </p>
                )}
              </div>
              <SourceBadge source={listing.source} variant="outline" />
            </div>

            {specs.length > 0 && (
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                {specs.map(({ label, value }) => (
                  <div key={label} className="rounded-xl border border-border/70 bg-surface/60 px-3 py-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wide text-muted">{label}</div>
                    <div className="mt-1 break-all text-[13px] font-semibold text-ink">{value}</div>
                  </div>
                ))}
              </div>
            )}

            {highlights.length > 0 && (
              <div className="flex flex-wrap gap-1.5 sm:hidden">
                {highlights.map((item, index) => (
                  <span
                    key={`${item}-${index}`}
                    className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink"
                  >
                    {item}
                  </span>
                ))}
              </div>
            )}

            {!hasAutoRiaDetails && listing.description && (
              <div>
                <h3 className="text-[13px] font-bold text-ink">Опис</h3>
                <p className="mt-2 text-[13px] leading-relaxed text-muted">{listing.description}</p>
              </div>
            )}

            {hasAutoRiaDetails && <AutoRiaListingDetails listing={listing} />}

            {listing.vin_checked && listing.source === "auto_ria" && (
              <p className="text-center text-[12px] font-medium text-emerald-dark">
                VIN-код перевірено на AUTO.RIA
              </p>
            )}

            <p className="pb-2 text-center text-[11px] text-muted">
              Дані надано{" "}
              <a
                href={listingAttributionUrl(listing.source, listing.url)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-dark hover:underline"
              >
                {listingSourceSiteName(listing.source)}
              </a>
            </p>
          </div>
        </div>

        <div className="shrink-0 border-t border-border bg-white px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-6">
          {favoriteError && (
            <p role="alert" className="mb-2 text-center text-[12px] font-medium text-red-600">
              {favoriteError}
            </p>
          )}

          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <Link href={listing.url} target="_blank" rel="noopener noreferrer" className="flex-1 sm:min-w-[240px]">
              <Button variant="emerald" size="lg" className="w-full gap-2 py-3 text-[15px] font-bold">
                <IconGlobe size={18} />
                {listingOpenLabel(listing.source)}
              </Button>
            </Link>
            {hasVinCheck(listing) && (
              <VinCheckButton listing={listing} size="md" className="w-full sm:w-auto sm:min-w-[180px]" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
