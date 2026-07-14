import type { Listing } from "@/types/api";

const AUTO_RIA_SITE = "https://auto.ria.com";
const VIN_RE = /^[A-HJ-NPR-Z0-9]{17}$/i;

function normalizeVin(value: string | null | undefined): string | null {
  const vin = (value || "").trim().toUpperCase();
  return VIN_RE.test(vin) ? vin : null;
}

/** Посилання на перевірку VIN на AUTO.RIA (для будь-якого джерела). */
export function getVinCheckUrl(listing: Listing): string | null {
  if (listing.vin_check_url) return listing.vin_check_url;

  // Оголошення AUTO.RIA — глибоке посилання на звіт по id оголошення
  const match = listing.id.match(/^auto_ria_(\d+)$/);
  if (match) {
    return `${AUTO_RIA_SITE}/vin-check/auto/${match[1]}/`;
  }

  // OLX / Telegram / інші — перевірка за самим VIN
  const vin = normalizeVin(listing.vin);
  if (vin) {
    return `${AUTO_RIA_SITE}/uk/check-car/?vinCode=${encodeURIComponent(vin)}`;
  }

  return null;
}

export function hasVinCheck(listing: Listing): boolean {
  return Boolean(getVinCheckUrl(listing));
}
