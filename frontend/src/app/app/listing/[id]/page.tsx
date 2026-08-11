"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { listings as listingsApi, favorites as favoritesApi } from "@/lib/api";
import type { Listing } from "@/types/api";
import { SourceBadge } from "@/components/listings/SourceBadge";
import { SourceLinks, listingSourceLinks } from "@/components/listings/SourceLinks";
import { PublishedTimeBadge } from "@/components/listings/PublishedTimeBadge";
import { AutoRiaListingDetails } from "@/components/listings/AutoRiaListingDetails";
import { VinCheckButton } from "@/components/listings/VinCheckButton";
import { Button } from "@/components/ui/Button";
import { IconArrowLeft, IconArrowRight, IconGlobe, IconHeart } from "@/components/icons";
import { useAuth } from "@/contexts/AuthProvider";
import {
  formatEngineVolume,
  resolveListingEngineVolume,
  resolveListingMileage,
} from "@/lib/listing-specs";
import {
  formatMileage,
  cn,
  publishedAgoLabel,
} from "@/lib/utils";
import { formatListingPrice, resolveDisplayCurrency } from "@/lib/display-currency";
import {
  listingAttributionUrl,
  listingOpenLabel,
  listingSourceSiteName,
} from "@/lib/listing-source";
import { hasVinCheck } from "@/lib/vin-check";
import { SellerContactBlock } from "@/components/listings/SellerContactBlock";
import { hasSellerContact } from "@/lib/seller-contact";

export default function ListingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useAuth();
  const [listing, setListing] = useState<Listing | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);
  const [photoIndex, setPhotoIndex] = useState(0);
  const galleryRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    params.then(p => {
      setLoading(true);
      setNotFound(false);
      listingsApi
        .get(p.id)
        .then(data => {
          setListing(data);
          setNotFound(false);
          if (
            data.source === "auto_ria" &&
            (data.images?.length ?? 0) < 2
          ) {
            listingsApi
              .ensurePhotos(data.id)
              .then(fresh => setListing(fresh))
              .catch(() => {});
          }
        })
        .catch(() => {
          setListing(null);
          setNotFound(true);
        })
        .finally(() => setLoading(false));
      if (user) {
        favoritesApi.check(p.id).then(r => setIsFavorite(r.is_favorite)).catch(() => {});
      }
    });
  }, [params, user]);

  const scrollToPhoto = useCallback((index: number) => {
    const container = galleryRef.current;
    if (!container) return;
    const slide = container.children[index] as HTMLElement | undefined;
    if (!slide) return;
    container.scrollTo({ left: slide.offsetLeft, behavior: "smooth" });
    setPhotoIndex(index);
  }, []);

  const toggleFavorite = async () => {
    if (!listing) return;
    if (!user) {
      router.push(`/auth/login?redirect=${encodeURIComponent(pathname)}`);
      return;
    }
    if (isFavorite) {
      await favoritesApi.remove(listing.id);
      setIsFavorite(false);
    } else {
      await favoritesApi.add(listing.id, listing);
      setIsFavorite(true);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
      </div>
    );
  }

  if (notFound || !listing) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
        <p className="text-[15px] font-semibold text-ink">Оголошення не знайдено</p>
        <p className="max-w-xs text-[13px] text-muted">
          Можливо, воно вже зняте з публікації або посилання застаріло.
        </p>
        <Link href={user ? "/app/dashboard" : "/"}>
          <Button variant="secondary" size="md">
            {user ? "До пошуків" : "На головну"}
          </Button>
        </Link>
      </div>
    );
  }

  const images = Array.isArray(listing.images) ? listing.images : [];
  const publishedLabel = publishedAgoLabel(listing.published_at);
  const hasAutoRiaDetails =
    listing.source === "auto_ria" &&
    listing.source_data &&
    Object.keys(listing.source_data).length > 0;

  const mileageKm = resolveListingMileage(listing);
  const engineVolume = resolveListingEngineVolume(listing);

  const specs = [
    { label: "Рік", value: listing.year > 0 ? String(listing.year) : null },
    {
      label: "Пробіг",
      value: mileageKm != null && mileageKm > 0 ? formatMileage(mileageKm) : null,
    },
    {
      label: "Обʼєм двигуна",
      value: engineVolume != null ? formatEngineVolume(engineVolume) : null,
    },
    { label: "Паливо", value: listing.fuel?.split(",")[0]?.trim() || null },
    { label: "КПП", value: listing.transmission || null },
    { label: "Регіон", value: listing.region?.split(",")[0]?.trim() || null },
    {
      label: "Продавець",
      value: listing.seller_type === "dealer" ? "Автосалон" : "Приват",
    },
  ].filter(item => item.value);

  return (
    <div className="w-full pb-4 lg:pb-0">
      <div className="mb-3 flex items-center justify-between gap-3 lg:mb-6">
        <button
          type="button"
          onClick={() => router.back()}
          className="inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-white px-3 py-1.5 text-[13px] font-medium text-ink shadow-sm lg:hidden"
        >
          <IconArrowLeft size={14} />
          Назад
        </button>
        <nav className="hidden min-w-0 flex-1 items-center gap-2 text-[12px] text-muted lg:flex">
          <Link href={user ? "/app/dashboard" : "/"} className="shrink-0 hover:text-ink">
            {user ? "Пошуки" : "Головна"}
          </Link>
          <span>/</span>
          <span className="truncate font-medium text-ink">{listing.title}</span>
        </nav>
        <button
          type="button"
          aria-label={isFavorite ? "Прибрати з обраного" : "Додати в обране"}
          onClick={() => void toggleFavorite()}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border/80 bg-white shadow-sm lg:hidden"
        >
          <IconHeart
            size={16}
            className={cn("transition-colors", isFavorite ? "fill-current text-emerald" : "text-muted/75")}
          />
        </button>
      </div>

      <div className="flex flex-col gap-4 lg:grid lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start lg:gap-6">
        {/* Left: gallery + details */}
        <div className="flex min-w-0 flex-col gap-4">
          <section className="-mx-4 overflow-hidden bg-white sm:mx-0 sm:rounded-2xl sm:border sm:border-border/80">
            <div className="relative aspect-[16/10] w-full bg-surface sm:aspect-[4/3]">
              {images.length > 0 ? (
                <div
                  ref={galleryRef}
                  className="flex h-full w-full snap-x snap-mandatory overflow-x-auto scroll-smooth scrollbar-hide touch-pan-x"
                  onScroll={e => {
                    const el = e.currentTarget;
                    const width = el.clientWidth || 1;
                    const index = Math.round(el.scrollLeft / width);
                    if (index !== photoIndex) setPhotoIndex(index);
                  }}
                >
                  {images.map((src, index) => (
                    <div
                      key={`${src}-${index}`}
                      className="relative h-full w-full shrink-0 snap-start snap-always"
                    >
                      <Image
                        src={src}
                        alt={`${listing.title} — фото ${index + 1}`}
                        fill
                        className="object-cover"
                        sizes="(max-width: 1024px) 100vw, 640px"
                        unoptimized
                        priority={index === 0}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex h-full items-center justify-center text-[13px] text-muted">
                  Без фото
                </div>
              )}

              {images.length > 1 && (
                <>
                  <button
                    type="button"
                    aria-label="Попереднє фото"
                    onClick={() =>
                      scrollToPhoto((photoIndex - 1 + images.length) % images.length)
                    }
                    className={cn(
                      "absolute left-2 top-1/2 z-[1] flex h-9 w-9 -translate-y-1/2 items-center justify-center",
                      "rounded-full bg-ink/70 text-white shadow-sm backdrop-blur-sm",
                      "active:bg-ink/85 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70",
                    )}
                  >
                    <IconArrowLeft size={16} />
                  </button>
                  <button
                    type="button"
                    aria-label="Наступне фото"
                    onClick={() => scrollToPhoto((photoIndex + 1) % images.length)}
                    className={cn(
                      "absolute right-2 top-1/2 z-[1] flex h-9 w-9 -translate-y-1/2 items-center justify-center",
                      "rounded-full bg-ink/70 text-white shadow-sm backdrop-blur-sm",
                      "active:bg-ink/85 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70",
                    )}
                  >
                    <IconArrowRight size={16} />
                  </button>
                  <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/55 px-2.5 py-1 text-[11px] font-semibold tabular-nums text-white backdrop-blur-sm">
                    {photoIndex + 1} / {images.length}
                  </div>
                </>
              )}
              <div className="pointer-events-none absolute bottom-3 left-3">
                <PublishedTimeBadge date={listing.published_at} short />
              </div>
            </div>

            {images.length > 1 && (
              <div className="flex gap-2 overflow-x-auto border-t border-border/70 px-3 py-3 scrollbar-hide sm:px-4">
                {images.map((src, index) => (
                  <button
                    key={`${src}-${index}-thumb`}
                    type="button"
                    onClick={() => scrollToPhoto(index)}
                    className={cn(
                      "relative h-14 w-20 shrink-0 overflow-hidden rounded-lg border-2 transition-colors",
                      index === photoIndex ? "border-emerald" : "border-transparent opacity-70",
                    )}
                  >
                    <Image src={src} alt="" fill className="object-cover" sizes="80px" unoptimized />
                  </button>
                ))}
              </div>
            )}
          </section>

          {/* Mobile summary */}
          <section className="rounded-2xl border border-border/80 bg-white p-4 shadow-sm lg:hidden">
            {(listing.alternate_sources?.length ?? 0) > 0 ? (
              <SourceLinks listing={listing} className="mb-2" />
            ) : (
              <SourceBadge source={listing.source} className="mb-2" />
            )}
            <h1 className="text-[18px] font-bold leading-snug text-ink">{listing.title}</h1>
            <p className="mt-1 text-[12px] text-muted">
              {listing.brand} {listing.model}
            </p>
            {publishedLabel && (
              <p className="mt-1 text-[12px] text-muted/80">{publishedLabel}</p>
            )}
            <div className="mt-3 text-[28px] font-black leading-none tracking-tight text-ink">
              {formatListingPrice(
                listing.price,
                listing.currency,
                resolveDisplayCurrency(user?.preferred_currency),
                listing.source_data,
              )}
            </div>
            <div className="mt-4 flex flex-col gap-2">
              {listingSourceLinks(listing).map((link, index) => (
                <a key={`${link.source}-${link.url}-m`} href={link.url} target="_blank" rel="noopener noreferrer">
                  <Button
                    variant={index === 0 ? "emerald" : "secondary"}
                    size="lg"
                    className="w-full gap-2 py-3 text-[15px] font-bold"
                  >
                    <IconGlobe size={18} />
                    {listingOpenLabel(link.source)}
                  </Button>
                </a>
              ))}
              {hasVinCheck(listing) && <VinCheckButton listing={listing} size="md" className="w-full" />}
            </div>
          </section>

          {specs.length > 0 && (
            <section className="rounded-2xl border border-border/80 bg-white p-4 sm:p-5">
              <h2 className="mb-3 text-[13px] font-bold text-ink">Характеристики</h2>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {specs.map(({ label, value }) => (
                  <div
                    key={label}
                    className="rounded-xl border border-border/70 bg-surface/60 px-3 py-2.5"
                  >
                    <div className="text-[10px] font-semibold uppercase tracking-wide text-muted">
                      {label}
                    </div>
                    <div className="mt-1 text-[13px] font-semibold text-ink">{value}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {hasSellerContact(listing) && <SellerContactBlock listing={listing} />}

          {!hasAutoRiaDetails && listing.description && (
            <section className="rounded-2xl border border-border/80 bg-white p-4 sm:p-6">
              <h2 className="mb-3 text-[15px] font-bold text-ink">Опис</h2>
              <p className="text-[13px] leading-relaxed text-muted whitespace-pre-wrap">
                {listing.description}
              </p>
            </section>
          )}

          {hasAutoRiaDetails && (
            <section className="rounded-2xl border border-border/80 bg-white p-4 sm:p-6">
              <AutoRiaListingDetails listing={listing} />
            </section>
          )}

          <p className="px-1 pb-2 text-center text-[11px] text-muted lg:pb-0">
            Дані надано{" "}
            {listingSourceLinks(listing).map((link, index, arr) => (
              <span key={`${link.source}-${link.url}-attr`}>
                {index > 0 ? (index === arr.length - 1 ? " та " : ", ") : null}
                <a
                  href={listingAttributionUrl(link.source, link.url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-dark hover:underline"
                >
                  {listingSourceSiteName(link.source)}
                </a>
              </span>
            ))}
          </p>
        </div>

        {/* Right: desktop sidebar */}
        <aside className="hidden lg:block lg:sticky lg:top-6">
          <div className="rounded-2xl border border-border/80 bg-white p-6 shadow-[0_2px_12px_-6px_rgba(10,12,14,0.12)]">
            <div className="mb-1 flex items-start justify-between gap-3">
              <h1 className="text-[18px] font-bold leading-snug text-ink">{listing.title}</h1>
              <button
                type="button"
                aria-label={isFavorite ? "Прибрати з обраного" : "Додати в обране"}
                onClick={() => void toggleFavorite()}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
              >
                <IconHeart
                  size={16}
                  className={cn("transition-colors", isFavorite ? "fill-current text-emerald" : "text-muted/75")}
                />
              </button>
            </div>
            <p className="text-[12px] text-muted">
              {listing.brand} {listing.model}
            </p>
            {publishedLabel && (
              <p className="mt-1 text-[12px] text-muted/80">{publishedLabel}</p>
            )}
            <div className="mt-4 text-[32px] font-black leading-none text-ink">
              {formatListingPrice(
                listing.price,
                listing.currency,
                resolveDisplayCurrency(user?.preferred_currency),
                listing.source_data,
              )}
            </div>
            <div className="mt-4">
              {(listing.alternate_sources?.length ?? 0) > 0 ? (
                <SourceLinks listing={listing} />
              ) : (
                <SourceBadge source={listing.source} variant="outline" />
              )}
            </div>
            <div className="mt-5 space-y-2">
              {listingSourceLinks(listing).map((link, index) => (
                <a key={`${link.source}-${link.url}-d`} href={link.url} target="_blank" rel="noopener noreferrer">
                  <Button
                    variant={index === 0 ? "emerald" : "secondary"}
                    size="lg"
                    className="w-full gap-2 py-3 text-[15px] font-bold"
                  >
                    <IconGlobe size={18} />
                    {listingOpenLabel(link.source)}
                  </Button>
                </a>
              ))}
              {hasVinCheck(listing) && <VinCheckButton listing={listing} size="md" className="w-full" />}
            </div>
            {hasSellerContact(listing) && <SellerContactBlock listing={listing} compact className="mt-4 shadow-sm" />}
          </div>
        </aside>
      </div>
    </div>
  );
}
