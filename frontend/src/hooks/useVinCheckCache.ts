"use client";

import { useEffect, useState } from "react";
import { getVinCheck, subscribeVinCheckCache, type StoredVinCheck } from "@/lib/vin-check-cache";

export function useVinCheckCache(vin: string | null | undefined): StoredVinCheck | null {
  const [cached, setCached] = useState<StoredVinCheck | null>(() => getVinCheck(vin));

  useEffect(() => {
    setCached(getVinCheck(vin));
    return subscribeVinCheckCache(() => setCached(getVinCheck(vin)));
  }, [vin]);

  return cached;
}
