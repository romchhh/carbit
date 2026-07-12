"use client";

import { useEffect, useState } from "react";
import { ListingsHorizontalCarousel } from "@/components/listings/ListingsHorizontalCarousel";
import { useAuth } from "@/contexts/AuthProvider";
import { listingSearch, getApiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Listing } from "@/types/api";

type Props = {
  variant?: "landing" | "dashboard";
  limit?: number;
};

export function FreshListingsCarousel({ variant = "landing", limit = 8 }: Props) {
  const embedded = variant === "dashboard";
  const { user } = useAuth();
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    listingSearch
      .search({ sources: ["auto_ria"] }, 1, limit, "published_desc", "browse")
      .then(data => {
        if (cancelled) return;
        setListings(data.items);
        setError(null);
      })
      .catch(err => {
        if (cancelled) return;
        setListings([]);
        setError(getApiErrorMessage(err, "Не вдалось завантажити оголошення"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [limit]);

  if (!loading && !error && listings.length === 0) {
    return null;
  }

  return (
    <div className={cn(!embedded && "bg-white py-10 sm:py-12")}>
      <div className={cn(!embedded && "mx-auto max-w-[1280px]")}>
        <ListingsHorizontalCarousel
          id="latest-listings"
          listings={listings}
          loading={loading}
          error={error}
          title="Останні пропозиції"
          description="Свіжі оголошення з AUTO.RIA — оновлюються в реальному часі"
          linkHref="/app/search"
          linkLabel="Усі результати"
          embedded={embedded}
          canFavorite={embedded || Boolean(user)}
          showNewBadge
        />
      </div>
    </div>
  );
}
