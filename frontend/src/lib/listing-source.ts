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
  uDrive: "udrive",
  Telegram: "telegram",
};

export function listingSourceLabel(source: string): string {
  if (source === "olx") return "OLX";
  if (source === "auto_ria") return "AUTO.RIA";
  if (source === "imperiya") return "Імперія Авто";
  if (source === "udrive") return "uDrive";
  if (source === "telegram") return "Telegram";
  return source.toUpperCase();
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
  if (source === "udrive") return "https://udrive.com.ua";
  if (source === "telegram") return "https://t.me";
  return "#";
}
