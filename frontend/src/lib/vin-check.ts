import type { Listing } from "@/types/api";

const AUTO_RIA_SITE = "https://auto.ria.com";

export function getVinCheckUrl(listing: Listing): string | null {
  if (listing.vin_check_url) return listing.vin_check_url;

  const match = listing.id.match(/^auto_ria_(\d+)$/);
  if (!match) return null;

  return `${AUTO_RIA_SITE}/vin-check/auto/${match[1]}/`;
}

export function hasVinCheck(listing: Listing): boolean {
  return listing.source === "auto_ria" && Boolean(getVinCheckUrl(listing));
}
