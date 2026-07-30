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

/** Повні слова — стебла «бенз»/«диз» + \b не матчать «бензин»/«дизель». */
const FUEL_WORD =
  "бензин(?:овий)?|дизель(?:ний|не)?|дизел|газ(?:овий)?|hybrid|petrol|diesel|benzin|dizel|gasoline";
const ENGINE_TRANS_HINT =
  `at|mt|cvt|dsg|tiptronic|автомат|мех|tsi|tdi|tdci|hdi|mpi|fsi|gdi|hybrid|plug|${FUEL_WORD}`;

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
    const keyLow = key.toLowerCase();
    if (
      (keyLow.includes("об") && keyLow.includes("єм")) ||
      keyLow.includes("engine") ||
      keyLow.includes("объем") ||
      keyLow.includes("двигун") ||
      keyLow.includes("motor")
    ) {
      const parsed = parseEngineNumber(value);
      if (parsed != null) return parsed;
    }
    if (typeof value === "string" && / л\b/i.test(value)) {
      const parsed = parseEngineNumber(value);
      if (parsed != null) return parsed;
    }
  }
  return null;
}

function inEngineRange(parsed: number | null): number | null {
  if (parsed == null) return null;
  if (parsed < 0.6 || parsed > 10) return null;
  return parsed;
}

function readEngineFromText(text: string): number | null {
  const blob = text.toLowerCase().replace(/\s+/g, " ").trim();
  if (!blob) return null;

  for (const pattern of [
    /(?:об['ʼ]?єм|двигун|мотор|engine|motor)\s*[:\-]?\s*(\d+[.,]?\d*)/i,
    /(\d+[.,]\d+)\s*(?:л|l|litre|liter|літр)\.?\b/i,
    /(\d{1,2})\s*(?:л|l|litre|liter|літр)\.?\b/i,
    // «бензин 3.0» / «Дизель, 2.99» — лише десяткове (не рік 2019)
    new RegExp(`(?:${FUEL_WORD})\\s*[,:]?\\s*(\\d+[.,]\\d+)`, "i"),
    // «бензин, 3 л»
    new RegExp(`(?:${FUEL_WORD})\\s*[,:]?\\s*(\\d{1,2})\\s*(?:л|l)\\.?`, "i"),
    // «3.0 бензин»
    new RegExp(`(\\d+[.,]\\d+)\\s*(?:${FUEL_WORD})`, "i"),
    /(\d{3,4})\s*(?:см3|см³|cc|куб\.?|cm3)\b/i,
  ]) {
    const match = blob.match(pattern);
    if (!match) continue;
    const parsed = inEngineRange(parseEngineNumber(match[1]));
    if (parsed != null) return parsed;
  }

  const transMatch = blob.match(new RegExp(`\\b(\\d+[.,]\\d+)\\s*(?:${ENGINE_TRANS_HINT})\\b`, "i"));
  if (transMatch) {
    const parsed = inEngineRange(parseEngineNumber(transMatch[1]));
    if (parsed != null) return parsed;
  }

  const trailingMatch = blob.match(/\b(\d\.\d)\b(?=\s*(?:$|[/|,]|—|-\s))/);
  if (trailingMatch) {
    const parsed = parseEngineNumber(trailingMatch[1]);
    if (parsed != null && parsed >= 0.8 && parsed <= 8) return parsed;
  }

  return null;
}

export function resolveListingEngineVolume(listing: Listing): number | null {
  if (typeof listing.engine_volume_l === "number" && listing.engine_volume_l > 0) {
    return listing.engine_volume_l;
  }

  const sd = asRecord(listing.source_data);
  const auto = asRecord(sd.autoData);
  const specs = asRecord(sd.specs);

  const fromData = readEngineFromSources(auto, specs, sd);
  if (fromData != null) return fromData;

  const fromSpecs = readEngineFromSpecValues(specs);
  if (fromSpecs != null) return fromSpecs;

  // AUTO.RIA fuelName: «Бензин, 3 л.»
  for (const fuelRaw of [auto.fuelName, sd.fuelName, listing.fuel]) {
    if (typeof fuelRaw === "string" && fuelRaw.trim()) {
      const fromFuel = readEngineFromText(fuelRaw);
      if (fromFuel != null) return fromFuel;
    }
  }

  const title = listing.title || "";
  const description = listing.description || "";
  return readEngineFromText(title) ?? readEngineFromText(description);
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
