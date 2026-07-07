"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { listings as listingsApi } from "@/lib/api";
import type { Listing } from "@/types/api";
import { SourceBadge } from "@/components/listings/SourceBadge";
import { PublishedTimeBadge } from "@/components/listings/PublishedTimeBadge";
import { Button } from "@/components/ui/Button";
import { IconHeart, IconGlobe, IconArrowRight } from "@/components/icons";
import { formatPrice, formatMileage, cn, publishedAgoLabel } from "@/lib/utils";
import { favorites as favoritesApi } from "@/lib/api";
import { normalizeListingForFavorite } from "@/lib/listing-favorite-payload";

export default function ListingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [listing, setListing] = useState<Listing | null>(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const [id, setId] = useState("");

  useEffect(() => {
    params.then(p => {
      setId(p.id);
      listingsApi.get(p.id).then(setListing).catch(() => setListing(null));
      favoritesApi.check(p.id).then(r => setIsFavorite(r.is_favorite)).catch(() => {});
    });
  }, [params]);

  const toggleFavorite = async () => {
    if (!listing) return;
    if (isFavorite) {
      await favoritesApi.remove(listing.id);
      setIsFavorite(false);
    } else {
      await favoritesApi.add(listing.id, normalizeListingForFavorite(listing));
      setIsFavorite(true);
    }
  };

  if (!listing) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const images = Array.isArray(listing.images) ? listing.images : [];
  const publishedLabel = publishedAgoLabel(listing.published_at);

  return (
    <div className="max-w-[960px]">
      <div className="flex items-center gap-2 text-[12px] text-muted mb-6">
        <Link href="/app/dashboard" className="hover:text-ink">Пошуки</Link>
        <span>/</span>
        <span className="text-ink font-medium">{listing.title}</span>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-5">
          <div className="bg-white border border-border rounded-xl overflow-hidden">
            <div className="relative w-full h-[280px] bg-surface">
              {images[0] ? (
                <Image
                  src={images[0]}
                  alt={listing.title}
                  fill
                  className="object-cover"
                  sizes="(max-width: 960px) 66vw, 640px"
                  unoptimized
                />
              ) : (
                <div className="flex h-full items-center justify-center text-[13px] text-muted">
                  Без фото
                </div>
              )}
              <div className="absolute bottom-3 left-3">
                <PublishedTimeBadge date={listing.published_at} short />
              </div>
            </div>
            {images.length > 1 && (
              <div className="flex gap-2 overflow-x-auto p-3 border-t border-border/70">
                {images.map((src, index) => (
                  <div
                    key={`${src}-${index}`}
                    className="relative h-14 w-20 shrink-0 overflow-hidden rounded-lg border border-border/70"
                  >
                    <Image src={src} alt="" fill className="object-cover" sizes="80px" unoptimized />
                  </div>
                ))}
              </div>
            )}
          </div>
          {listing.description && (
            <div className="bg-white border border-border rounded-xl p-6">
              <h2 className="text-[15px] font-bold text-ink mb-3">Опис</h2>
              <p className="text-[13px] text-muted leading-relaxed whitespace-pre-wrap">{listing.description}</p>
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <div className="bg-white border border-border rounded-xl p-6 sticky top-[80px]">
            <div className="flex items-start justify-between mb-1">
              <h1 className="text-[16px] font-bold text-ink">{listing.title}</h1>
              <button
                type="button"
                aria-label={isFavorite ? "Прибрати з обраного" : "Додати в обране"}
                onClick={toggleFavorite}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-transparent"
              >
                <IconHeart
                  size={16}
                  className={cn("transition-colors", isFavorite ? "fill-current text-emerald" : "text-muted/75")}
                />
              </button>
            </div>
            <p className="text-[12px] text-muted mb-1">
              {listing.year} · {formatMileage(listing.mileage)} · {listing.region}
            </p>
            {publishedLabel && (
              <p className="text-[12px] text-muted/80 mb-4">{publishedLabel}</p>
            )}
            {!publishedLabel && <div className="mb-4" />}
            <div className="text-[32px] font-black text-ink mb-4">{formatPrice(listing.price, listing.currency)}</div>
            <SourceBadge source={listing.source} variant="outline" className="mb-4" />
            <div className="space-y-2">
              <a href={listing.url} target="_blank" rel="noopener noreferrer">
                <Button variant="primary" size="md" className="w-full gap-1.5">
                  <IconGlobe size={13} /> Відкрити оригінал
                </Button>
              </a>
              <Link href="/app/dashboard">
                <Button variant="secondary" size="md" className="w-full gap-1.5">
                  <IconArrowRight size={13} /> До пошуків
                </Button>
              </Link>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
