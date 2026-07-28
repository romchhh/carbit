import type { Listing } from "@/types/api";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function normalizeEngineLitres(raw: number): number | null {
  if (!Number.isFinite(raw) || raw <= 0) return null;
  if (raw >= 100) return Math.round((raw / 1000) * 100) / 100;
  if (raw <= 20) return Math.round(raw * 10) / 10;
  return null;
}

function parseEngineNumber(raw: unknown): number | null {
  if (typeof raw === "number") return normalizeEngineLitres(raw);
  if (typeof raw === "string") {
    const match = raw.replace(/\s/g, "").match(/([\d]+[.,]?\d*)/);
    if (!match) return null;
    return normalizeEngineLitres(Number(match[1].replace(",", ".")));
  }
  if (raw && typeof raw === "object") {
    const block = raw as Record<string, unknown>;
    for (const key of ["liters", "litres", "value", "l"]) {
      const parsed = parseEngineNumber(block[key]);
      if (parsed != null) return parsed;
    }
  }
  return null;
}

function readEngineFromSources(...sources: Record<string, unknown>[]): number | null {
  for (const source of sources) {
    for (const key of [
      "engineVolume",
      "engineVolumeLitres",
      "engine_volume",
      "engine_volume_l",
      "volumeLitres",
      "volume",
      "engine",
    ]) {
      const parsed = parseEngineNumber(source[key]);
      if (parsed != null) return parsed;
    }
  }
  return null;
}

function readEngineFromSpecValues(specs: Record<string, unknown>): number | null {
  for (const [key, value] of Object.entries(specs)) {
    if (typeof value !== "string") continue;
    const keyLow = key.toLowerCase();
    const valueLow = value.toLowerCase();
    if (
      (keyLow.includes("об") && keyLow.includes("єм")) ||
      keyLow.includes("engine") ||
      keyLow.includes("объем") ||
      valueLow.includes(" л")
    ) {
      const parsed = parseEngineNumber(value);
      if (parsed != null) return parsed;
    }
  }
  return null;
}

export function resolveListingEngineVolume(listing: Listing): number | null {
  const sd = asRecord(listing.source_data);
  const auto = asRecord(sd.autoData);
  const specs = asRecord(sd.specs);

  const fromData = readEngineFromSources(auto, specs, sd);
  if (fromData != null) return fromData;

  const fromSpecs = readEngineFromSpecValues(specs);
  if (fromSpecs != null) return fromSpecs;

  const blob = `${listing.title} ${listing.description ?? ""}`.toLowerCase();
  for (const pattern of [
    /(\d+[.,]\d+)\s*л\b/,
    /(\d+[.,]\d+)\s*(?:l|liter|litre)\b/,
    /об['ʼ]?єм[^\d]{0,8}(\d+[.,]\d+)/,
  ]) {
    const match = blob.match(pattern);
    if (!match) continue;
    const litres = Number(match[1].replace(",", "."));
    if (litres >= 0.5 && litres <= 20) return Math.round(litres * 10) / 10;
  }
  return null;
}

function parseMileageNumber(raw: unknown): number | null {
  if (typeof raw === "number" && raw > 0) return Math.round(raw);
  if (typeof raw !== "string") return null;
  const normalized = raw.replace(/\s/g, "").toLowerCase();
  const match = normalized.match(/([\d.,]+)/);
  if (!match) return null;
  const value = Number(match[1].replace(",", "."));
  if (!Number.isFinite(value) || value <= 0) return null;
  if (/тис|тыс|k\b/.test(normalized) && value < 1000) return Math.round(value * 1000);
  return Math.round(value);
}

export function resolveListingMileage(listing: Listing): number | null {
  if (listing.mileage > 0) return listing.mileage;

  const sd = asRecord(listing.source_data);
  const auto = asRecord(sd.autoData);
  const specs = asRecord(sd.specs);

  const raceInt = auto.raceInt;
  if (typeof raceInt === "number" && raceInt > 0) return Math.round(raceInt * 1000);

  for (const source of [specs, sd]) {
    for (const key of ["mileage", "race", "raceInt", "mileage_km"]) {
      const parsed = parseMileageNumber(source[key]);
      if (parsed != null) return parsed;
    }
  }

  for (const value of Object.values(specs)) {
    if (typeof value !== "string") continue;
    const low = value.toLowerCase();
    if (!low.includes("проб") && !low.includes("mileage")) continue;
    const parsed = parseMileageNumber(value);
    if (parsed != null) return parsed;
  }

  return null;
}

export function formatEngineVolume(litres: number): string {
  const rounded = Math.round(litres * 10) / 10;
  return `${rounded.toLocaleString("uk-UA", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} л`;
}
