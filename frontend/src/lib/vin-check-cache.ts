import type { VinCheckResult } from "@/types/api";
import type { Listing } from "@/types/api";
import { resolveListingVin } from "@/lib/vin-check";

const KEY = "carbit:vin-checks:v3";
const MAX_ITEMS = 40;
const EVENT = "carbit:vin-check-changed";

export type StoredVinCheck = {
  vin: string;
  listingId?: string;
  listingIds?: string[];
  checkedAt: string;
  result: VinCheckResult;
};

function readAll(): Record<string, StoredVinCheck> {
  if (typeof window === "undefined") return {};
  const raw = localStorage.getItem(KEY);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed as Record<string, StoredVinCheck>;
  } catch {
    return {};
  }
}

function writeAll(data: Record<string, StoredVinCheck>) {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEY, JSON.stringify(data));
  window.dispatchEvent(new CustomEvent(EVENT));
}

function listingIdsOf(row: StoredVinCheck): string[] {
  const ids = [...(row.listingIds || [])];
  if (row.listingId && !ids.includes(row.listingId)) ids.push(row.listingId);
  return ids;
}

/** Збережена перевірка за VIN (ключ — нормалізований VIN). */
export function getVinCheck(vin: string | null | undefined): StoredVinCheck | null {
  const code = (vin || "").trim().toUpperCase();
  if (!code) return null;
  const row = readAll()[code];
  if (!row?.result || row.vin !== code) return null;
  return row;
}

export function getVinCheckByListingId(listingId: string | null | undefined): StoredVinCheck | null {
  const id = (listingId || "").trim();
  if (!id) return null;
  for (const row of Object.values(readAll())) {
    if (!row?.result) continue;
    if (listingIdsOf(row).includes(id)) return row;
  }
  return null;
}

/** Перевірка, закріплена за оголошенням: спочатку VIN, потім id картки. */
export function getVinCheckForListing(listing: Listing): StoredVinCheck | null {
  return getVinCheck(resolveListingVin(listing)) || getVinCheckByListingId(listing.id);
}

export function saveVinCheck(
  vin: string,
  result: VinCheckResult,
  listingId?: string | null,
): StoredVinCheck {
  const code = vin.trim().toUpperCase();
  const prev = readAll()[code];
  const listingIds = listingIdsOf(prev || { vin: code, checkedAt: "", result });
  if (listingId && !listingIds.includes(listingId)) listingIds.push(listingId);

  const entry: StoredVinCheck = {
    vin: code,
    listingId: listingId ?? prev?.listingId ?? listingIds[0],
    listingIds: listingIds.length ? listingIds : undefined,
    checkedAt: new Date().toISOString(),
    result,
  };

  const all = readAll();
  all[code] = entry;

  const sorted = Object.values(all).sort(
    (a, b) => new Date(b.checkedAt).getTime() - new Date(a.checkedAt).getTime(),
  );
  const trimmed = sorted.slice(0, MAX_ITEMS);
  const next: Record<string, StoredVinCheck> = {};
  for (const item of trimmed) {
    next[item.vin] = item;
  }

  writeAll(next);
  return entry;
}

export function subscribeVinCheckCache(listener: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}
