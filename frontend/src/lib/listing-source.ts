import { SOURCE_LOGOS } from "@/lib/brand-assets";

export function listingSourceLabel(source: string): string {
  if (source === "olx") return "OLX";
  if (source === "auto_ria") return "AUTO.RIA";
  if (source === "telegram") return "Telegram";
  return source.toUpperCase();
}

export function listingSourceIcon(source: string): string | null {
  if (source === "auto_ria") return SOURCE_LOGOS.autoRia;
  if (source === "olx") return SOURCE_LOGOS.olx;
  if (source === "telegram") return SOURCE_LOGOS.telegram;
  return null;
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
  if (source === "telegram") return "https://t.me";
  return "#";
}
