"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { IconHeart, IconArrowRight } from "@/components/icons";
import { favorites as favoritesApi, ApiError } from "@/lib/api";
import { AppEmpty, AppLoading, AppPage, AppSection } from "@/components/layout/AppPage";
import type { Favorite } from "@/types/api";
import { formatPrice } from "@/lib/utils";

export default function FavoritesPage() {
  const [items, setItems] = useState<Favorite[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setItems(await favoritesApi.list());
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const remove = async (listingId: string) => {
    try {
      await favoritesApi.remove(listingId);
      setItems(prev => prev.filter(f => f.listing_id !== listingId));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Помилка");
    }
  };

  if (loading) return <AppLoading />;

  return (
    <AppPage title="Обране" description="Збережені авто для швидкого доступу">
      {items.length === 0 ? (
        <AppEmpty>
          <IconHeart size={32} className="mx-auto mb-4 text-muted/30" />
          <p className="text-muted">Поки що немає обраних авто</p>
          <Link href="/app/dashboard" className="mt-4 inline-block">
            <Button variant="primary" size="md">До пошуків</Button>
          </Link>
        </AppEmpty>
      ) : (
        <div className="space-y-3">
          {items.map(({ id, listing }) => (
            <AppSection key={id} className="!bg-white">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <h3 className="text-[15px] font-bold text-ink">{listing.title}</h3>
                  <p className="mt-1 text-[12px] text-muted">
                    {listing.year} · {listing.mileage.toLocaleString("uk-UA")} км · {listing.region}
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-[18px] font-black text-ink">{formatPrice(listing.price)}</span>
                    <Badge variant="outline">{listing.source}</Badge>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <Link href={`/app/listing/${listing.id}`}>
                    <Button variant="secondary" size="sm" className="gap-1">
                      Деталі <IconArrowRight size={11} />
                    </Button>
                  </Link>
                  <button onClick={() => remove(listing.id)} className="text-[12px] text-red-500 hover:underline">
                    Видалити
                  </button>
                </div>
              </div>
            </AppSection>
          ))}
        </div>
      )}
    </AppPage>
  );
}
