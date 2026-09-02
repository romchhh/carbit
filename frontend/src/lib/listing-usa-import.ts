import type { Listing } from "@/types/api";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function normText(value: string): string {
  return value
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/\s+/g, " ")
    .trim();
}

/** Ті самі маркери, що й `usa_import` у backend advanced_filters. */
const USA_TOKENS = ["сша", "usa", "america", "штати", "америк", "copart", "iaai"] as const;

function mentionsUsa(text: string): boolean {
  const norm = normText(text);
  return USA_TOKENS.some(token => norm.includes(token));
}

function specKeyIsImportOrigin(key: string): boolean {
  const norm = normText(key);
  return norm.includes("пригнано") || norm.includes("car from") || norm.includes("звідки");
}

function collectHaystack(listing: Listing): string {
  const sd = asRecord(listing.source_data);
  const specs = asRecord(sd.specs);
  const auto = asRecord(sd.autoData);
  const parts = [
    listing.title,
    listing.description || "",
    listing.fuel || "",
    listing.transmission || "",
  ];
  for (const value of Object.values(specs)) {
    if (typeof value === "string") parts.push(value);
  }
  for (const value of Object.values(auto)) {
    if (typeof value === "string" || typeof value === "number") parts.push(String(value));
  }
  return normText(parts.join(" "));
}

/** true — пригнано з США; API-поле + fallback для старих кешів. */
export function resolveListingUsaImport(listing: Listing): boolean {
  if (listing.usa_import === true) return true;
  if (listing.usa_import === false) return false;

  const sd = asRecord(listing.source_data);
  const flags = asRecord(sd.condition_flags);
  if (flags.usa_import === true) return true;

  const specs = asRecord(sd.specs);

  for (const [key, value] of Object.entries(specs)) {
    if (typeof value !== "string") continue;
    if (specKeyIsImportOrigin(key) && mentionsUsa(value)) return true;
  }

  const fromUsa = sd.from_usa ?? asRecord(sd.autoData).from_usa;
  if (fromUsa === 1 || fromUsa === true || fromUsa === "1") return true;

  const haystack = collectHaystack(listing);

  if (
    haystack.includes("з сша") ||
    haystack.includes("зі сша") ||
    haystack.includes("з usa") ||
    haystack.includes("з америк")
  ) {
    return true;
  }

  if (/пригнан\w*\s+(?:з|зі)\s+(?:сша|usa|america|штати|америк)/.test(haystack)) {
    return true;
  }

  return USA_TOKENS.some(token => haystack.includes(token));
}

export const LISTING_USA_IMPORT_LABEL = "🇺🇸 Пригнано з США";
export const LISTING_USA_IMPORT_SHORT_LABEL = "🇺🇸 З США";
