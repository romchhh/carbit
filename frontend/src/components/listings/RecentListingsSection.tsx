"use client";

import { useEffect, useState } from "react";
import { ListingsHorizontalCarousel } from "@/components/listings/ListingsHorizontalCarousel";
import { loadRecentListings } from "@/lib/recent-listings";
import type { Listing } from "@/types/api";

type Props = {
  limit?: number;
  className?: string;
};

export function RecentListingsSection({ limit = 6, className }: Props) {
  const [items, setItems] = useState<Listing[]>([]);

  useEffect(() => {
    const sync = () => setItems(loadRecentListings().slice(0, limit));
    sync();
    window.addEventListener("carbit:recent-listings-changed", sync);
    return () => window.removeEventListener("carbit:recent-listings-changed", sync);
  }, [limit]);

  if (items.length === 0) return null;

  return (
    <ListingsHorizontalCarousel
      className={className}
      listings={items}
      title="Останні переглянуті"
      description="Пропозиції, які ви відкривали нещодавно"
      embedded
      canFavorite
    />
  );
}
