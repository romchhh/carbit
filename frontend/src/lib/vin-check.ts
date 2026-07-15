import type { Listing } from "@/types/api";

const AUTO_RIA_SITE = "https://auto.ria.com";
const VIN_RE = /^[A-HJ-NPR-Z0-9]{17}$/i;
const VIN_CANDIDATE_RE = /\b[A-HJ-NPR-Z0-9]{17}\b/gi;

export function normalizeVin(value: string | null | undefined): string | null {
  const vin = (value || "").replace(/[^A-HJ-NPR-Z0-9]/gi, "").toUpperCase();
  return VIN_RE.test(vin) ? vin : null;
}

function extractVinFromText(text: string | null | undefined): string | null {
  if (!text) return null;
  for (const match of text.matchAll(VIN_CANDIDATE_RE)) {
    const vin = normalizeVin(match[0]);
    if (vin) return vin;
  }
  return null;
}

function collectSourceText(value: unknown, depth = 0): string {
  if (depth > 4 || value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    return value.map(item => collectSourceText(item, depth + 1)).join("\n");
  }
  if (typeof value === "object") {
    return Object.values(value as Record<string, unknown>)
      .map(item => collectSourceText(item, depth + 1))
      .join("\n");
  }
  return "";
}

/** Валідний VIN з поля listing або з опису / source_data. */
export function resolveListingVin(listing: Listing): string | null {
  const direct = normalizeVin(listing.vin);
  if (direct) return direct;

  const fromDescription = extractVinFromText(listing.description || "");
  if (fromDescription) return fromDescription;

  const fromTitle = extractVinFromText(listing.title || "");
  if (fromTitle) return fromTitle;

  return extractVinFromText(collectSourceText(listing.source_data));
}

/** Зовнішнє посилання AUTO.RIA — додатковий fallback, якщо VIN немає. */
export function getVinCheckUrl(listing: Listing): string | null {
  if (listing.vin_check_url) return listing.vin_check_url;

  const match = listing.id.match(/^auto_ria_(\d+)$/);
  if (match) {
    return `${AUTO_RIA_SITE}/vin-check/auto/${match[1]}/`;
  }

  const vin = resolveListingVin(listing);
  if (vin) {
    return `${AUTO_RIA_SITE}/uk/check-car/?vinCode=${encodeURIComponent(vin)}`;
  }

  return null;
}

export function hasVinCheck(listing: Listing): boolean {
  return Boolean(resolveListingVin(listing) || getVinCheckUrl(listing));
}
