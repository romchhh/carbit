import type { Listing } from "@/types/api";

const VIN_RE = /^[A-HJ-NPR-Z0-9]{17}$/i;

export function normalizeVin(value: string | null | undefined): string | null {
  const vin = (value || "").trim().toUpperCase();
  return VIN_RE.test(vin) ? vin : null;
}

/** Чи можна перевірити VIN у Carbit (База ДАІ). */
export function hasVinCheck(listing: Listing): boolean {
  return Boolean(normalizeVin(listing.vin));
}

export function getBazaGaiVinUrl(vin: string): string {
  return `https://baza-gai.com.ua/vin/${encodeURIComponent(vin.trim().toUpperCase())}`;
}
