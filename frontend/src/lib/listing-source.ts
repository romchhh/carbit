import { SOURCE_LOGOS } from "@/lib/brand-assets";

/** Ключі API / listing.source */
const SOURCE_ICON_KEYS = {
  auto_ria: SOURCE_LOGOS.autoRia,
  olx: SOURCE_LOGOS.olx,
  imperiya: SOURCE_LOGOS.imperiya,
  udrive: SOURCE_LOGOS.udrive,
  telegram: SOURCE_LOGOS.telegram,
} as const;

/** Підписи з фільтра SearchFilterState.sources */
const SOURCE_FILTER_LABEL_TO_KEY: Record<string, keyof typeof SOURCE_ICON_KEYS> = {
  "AUTO.RIA": "auto_ria",
  OLX: "olx",
  "Імперія Авто": "imperiya",
  "Car Market": "car_market",
  uDrive: "udrive",
  Telegram: "telegram",
};

export function listingSourceLabel(source: string): string {
  if (source === "olx") return "OLX";
  if (source === "auto_ria") return "AUTO.RIA";
  if (source === "imperiya") return "Імперія Авто";
  if (source === "car_market") return "Car Market";
  if (source === "udrive") return "uDrive";
  if (source === "telegram") return "Telegram";
  return source.toUpperCase();
}

/** Нові = 2025–2026 і ≤1000 км; uDrive — завжди нові з салону. */
export const NEW_CAR_YEAR_MIN = 2025;
export const NEW_CAR_YEAR_MAX = 2026;
export const NEW_CAR_MILEAGE_MAX_KM = 1000;

function isUdriveListing(listing: {
  id?: string | null;
  source?: string | null;
}): boolean {
  const id = listing.id || "";
  return id.startsWith("udrive_") || (listing.source || "").toLowerCase() === "udrive";
}

export function listingIsNewCar(listing: {
  id?: string | null;
  source?: string | null;
  year?: number | null;
  mileage?: number | null;
}): boolean {
  if (isUdriveListing(listing)) return true;
  const year = Number(listing.year) || 0;
  const mileage = Number(listing.mileage) || 0;
  if (year < NEW_CAR_YEAR_MIN || year > NEW_CAR_YEAR_MAX) return false;
  return mileage <= NEW_CAR_MILEAGE_MAX_KM;
}

export function listingSourceIcon(source: string): string | null {
  const key = source as keyof typeof SOURCE_ICON_KEYS;
  if (key in SOURCE_ICON_KEYS) return SOURCE_ICON_KEYS[key];
  return null;
}

/** Іконка для чіпів фільтра «Джерела» (AUTO.RIA, OLX, …). */
export function sourceFilterIcon(sourceLabel: string): string | null {
  const key = SOURCE_FILTER_LABEL_TO_KEY[sourceLabel];
  return key ? SOURCE_ICON_KEYS[key] : null;
}

export function listingSourceSiteName(source: string): string {
  return listingSourceLabel(source);
}

export function listingOpenLabel(source: string): string {
  if (source === "telegram") return "Відкрити в Telegram";
  return `Відкрити на ${listingSourceLabel(source)}`;
}

export function listingAttributionUrl(source: string, listingUrl?: string): string {
  if (listingUrl) return listingUrl;
  if (source === "olx") return "https://www.olx.ua";
  if (source === "auto_ria") return "https://auto.ria.com";
  if (source === "imperiya") return "https://imperiya-auto.com.ua";
  if (source === "car_market") return "https://car-market.net";
  if (source === "udrive") return "https://udrive.com.ua";
  if (source === "telegram") return "https://t.me";
  return "#";
}
