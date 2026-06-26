"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listings as listingsApi } from "@/lib/api";
import type { Listing } from "@/types/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { IconHeart, IconGlobe, IconArrowRight } from "@/components/icons";
import { formatPrice, formatMileage } from "@/lib/utils";
import { favorites as favoritesApi } from "@/lib/api";

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
      await favoritesApi.add(listing.id);
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
            <div className="w-full h-[280px] bg-surface flex items-center justify-center text-muted text-[13px]">
              Фото оголошення
            </div>
          </div>
          {listing.description && (
            <div className="bg-white border border-border rounded-xl p-6">
              <h2 className="text-[15px] font-bold text-ink mb-3">Опис</h2>
              <p className="text-[13px] text-muted leading-relaxed">{listing.description}</p>
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <div className="bg-white border border-border rounded-xl p-6 sticky top-[80px]">
            <div className="flex items-start justify-between mb-1">
              <h1 className="text-[16px] font-bold text-ink">{listing.title}</h1>
              <button onClick={toggleFavorite} className="w-8 h-8 rounded-lg border border-border flex items-center justify-center">
                <IconHeart size={14} className={isFavorite ? "text-red-500" : "text-muted"} />
              </button>
            </div>
            <p className="text-[12px] text-muted mb-4">
              {listing.year} · {formatMileage(listing.mileage)} · {listing.region}
            </p>
            <div className="text-[32px] font-black text-ink mb-4">{formatPrice(listing.price, listing.currency)}</div>
            <Badge variant="outline" className="mb-4">{listing.source}</Badge>
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
