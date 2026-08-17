"use client";

import { useEffect, useState } from "react";
import {
  getVinCheck,
  getVinCheckByListingId,
  subscribeVinCheckCache,
  type StoredVinCheck,
} from "@/lib/vin-check-cache";
import { resolveListingVin } from "@/lib/vin-check";
import type { Listing } from "@/types/api";

export function useVinCheckCache(vin: string | null | undefined): StoredVinCheck | null {
  const [cached, setCached] = useState<StoredVinCheck | null>(() => getVinCheck(vin));

  useEffect(() => {
    setCached(getVinCheck(vin));
    return subscribeVinCheckCache(() => setCached(getVinCheck(vin)));
  }, [vin]);

  return cached;
}

export function useListingVinCheck(listing: Listing): StoredVinCheck | null {
  const listingId = listing.id;
  const vin = resolveListingVin(listing);
  const [cached, setCached] = useState<StoredVinCheck | null>(
    () => getVinCheck(vin) || getVinCheckByListingId(listingId),
  );

  useEffect(() => {
    const read = () => getVinCheck(vin) || getVinCheckByListingId(listingId);
    setCached(read());
    return subscribeVinCheckCache(() => setCached(read()));
  }, [listingId, vin]);

  return cached;
}
