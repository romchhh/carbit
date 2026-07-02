"use client";

import { useCallback, useEffect, useState } from "react";
import { ListingsHorizontalCarousel } from "@/components/listings/ListingsHorizontalCarousel";
import { FAVORITES_CHANGED_EVENT } from "@/hooks/useListingFavorite";
import { favorites as favoritesApi } from "@/lib/api";
import type { Listing } from "@/types/api";

type Props = {
  limit?: number;
  className?: string;
};

export function FavoriteListingsSection({ limit = 8, className }: Props) {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const items = await favoritesApi.list();
      setListings(items.slice(0, limit).map(item => item.listing));
    } catch {
      setListings([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const onChange = () => {
      void load();
    };
    window.addEventListener(FAVORITES_CHANGED_EVENT, onChange);
    return () => window.removeEventListener(FAVORITES_CHANGED_EVENT, onChange);
  }, [load]);

  if (!loading && listings.length === 0) return null;

  return (
    <ListingsHorizontalCarousel
      className={className}
      listings={listings}
      loading={loading}
      title="Обране"
      description="Збережені авто для швидкого доступу"
      linkHref="/app/favorites"
      linkLabel="Усі обрані"
      embedded
      canFavorite
    />
  );
}
