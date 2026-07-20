import type { SearchFilterState } from "@/lib/search-catalog";
import { DEFAULT_FILTERS } from "@/lib/search-catalog";

export type BackendSearchFilters = {
  brand?: string | null;
  model?: string | null;
  year_from?: number | null;
  year_to?: number | null;
  price_from?: number | null;
  price_to?: number | null;
  currency?: "USD" | "UAH" | "EUR" | null;
  mileage_from?: number | null;
  mileage_to?: number | null;
  fuel?: string[] | null;
  transmission?: string[] | null;
  region?: string | null;
  sources?: string[] | null;
  category?: string | null;
  engine_volume_from?: number | null;
  engine_volume_to?: number | null;
  drivetrain?: string[] | null;
  colors?: string[] | null;
  fuel_consumption_from?: number | null;
  fuel_consumption_to?: number | null;
  ev_range_from?: number | null;
  ev_range_to?: number | null;
  battery_capacity_from?: number | null;
  battery_capacity_to?: number | null;
  power_from?: number | null;
  power_to?: number | null;
  published_within_days?: number | null;
};

const SOURCE_TO_BACKEND: Record<string, string> = {
  "AUTO.RIA": "auto_ria",
  OLX: "olx",
  Telegram: "telegram",
};

function parseNumber(value: string): number | null {
  const digits = value.replace(/[^\d]/g, "");
  if (!digits) return null;
  const num = Number(digits);
  return Number.isFinite(num) ? num : null;
}

function parseDecimal(value: string): number | null {
  const normalized = value.replace(",", ".").replace(/[^\d.]/g, "");
  if (!normalized) return null;
  const num = Number(normalized);
  return Number.isFinite(num) ? num : null;
}

function parseThousandsKm(value: string): number | null {
  const num = parseNumber(value);
  if (num == null) return null;
  return num * 1000;
}

function mapSources(sources: string[]): string[] | null {
  const mapped = sources
    .map(source => SOURCE_TO_BACKEND[source])
    .filter((source): source is string => Boolean(source));

  return mapped.length ? mapped : null;
}

export function toBackendSearchFilters(filters: SearchFilterState): BackendSearchFilters {
  return {
    brand: filters.brand || null,
    model: filters.model || null,
    year_from: parseNumber(filters.yearFrom),
    year_to: parseNumber(filters.yearTo),
    price_from: parseNumber(filters.priceFrom),
    price_to: parseNumber(filters.priceTo),
    currency: filters.currency || "USD",
    mileage_from: parseThousandsKm(filters.mileageFrom),
    mileage_to: parseThousandsKm(filters.mileageTo),
    fuel: filters.fuels.length ? [...filters.fuels] : null,
    transmission: filters.transmissions.length ? [...filters.transmissions] : null,
    region: filters.region || null,
    sources: mapSources(filters.sources),
    category: filters.category !== "all" ? filters.category : null,
    engine_volume_from: parseDecimal(filters.engineVolumeFrom),
    engine_volume_to: parseDecimal(filters.engineVolumeTo),
    drivetrain: filters.driveTypes.length ? [...filters.driveTypes] : null,
    colors: filters.colors.length ? [...filters.colors] : null,
    fuel_consumption_from: parseDecimal(filters.fuelConsumptionFrom),
    fuel_consumption_to: parseDecimal(filters.fuelConsumptionTo),
    ev_range_from: parseNumber(filters.rangeFrom),
    ev_range_to: parseNumber(filters.rangeTo),
    battery_capacity_from: parseDecimal(filters.batteryCapacityFrom),
    battery_capacity_to: parseDecimal(filters.batteryCapacityTo),
    power_from: parseNumber(filters.powerFrom),
    power_to: parseNumber(filters.powerTo),
  };
}

function formatThousandsKm(km: number | null | undefined): string {
  if (km == null || !Number.isFinite(km) || km <= 0) return "";
  return String(Math.round(km / 1000));
}

function formatPlainNumber(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "";
  return String(value);
}

const BACKEND_SOURCE_TO_UI: Record<string, string> = {
  auto_ria: "AUTO.RIA",
  olx: "OLX",
  telegram: "Telegram",
};

/** Відновлює UI-фільтри зі збереженого моніторингу. */
export function fromBackendSearchFilters(
  raw: Record<string, unknown> | null | undefined,
): SearchFilterState {
  const base = { ...DEFAULT_FILTERS };
  if (!raw || typeof raw !== "object") return base;

  const category = String(raw.category || "all");
  const currencyRaw = String(raw.currency || "USD").toUpperCase();
  const currency =
    currencyRaw === "UAH" || currencyRaw === "EUR" || currencyRaw === "USD"
      ? currencyRaw
      : "USD";

  const sourcesRaw = Array.isArray(raw.sources) ? raw.sources.map(String) : [];
  const sources = sourcesRaw
    .map(s => BACKEND_SOURCE_TO_UI[s] || s)
    .filter(Boolean);

  return {
    ...base,
    name: "",
    category: (["all", "used", "new", "import"].includes(category)
      ? category
      : "all") as SearchFilterState["category"],
    brand: String(raw.brand || ""),
    model: String(raw.model || ""),
    yearFrom: formatPlainNumber(raw.year_from as number | null),
    yearTo: formatPlainNumber(raw.year_to as number | null),
    priceFrom: formatPlainNumber(raw.price_from as number | null),
    priceTo: formatPlainNumber(raw.price_to as number | null),
    currency,
    mileageFrom: formatThousandsKm(raw.mileage_from as number | null),
    mileageTo: formatThousandsKm(raw.mileage_to as number | null),
    fuels: Array.isArray(raw.fuel) ? raw.fuel.map(String) : [],
    transmissions: Array.isArray(raw.transmission) ? raw.transmission.map(String) : [],
    region: String(raw.region || ""),
    sources,
    engineVolumeFrom: formatPlainNumber(raw.engine_volume_from as number | null),
    engineVolumeTo: formatPlainNumber(raw.engine_volume_to as number | null),
    driveTypes: Array.isArray(raw.drivetrain) ? raw.drivetrain.map(String) : [],
    colors: Array.isArray(raw.colors) ? raw.colors.map(String) : [],
    fuelConsumptionFrom: formatPlainNumber(raw.fuel_consumption_from as number | null),
    fuelConsumptionTo: formatPlainNumber(raw.fuel_consumption_to as number | null),
    rangeFrom: formatPlainNumber(raw.ev_range_from as number | null),
    rangeTo: formatPlainNumber(raw.ev_range_to as number | null),
    batteryCapacityFrom: formatPlainNumber(raw.battery_capacity_from as number | null),
    batteryCapacityTo: formatPlainNumber(raw.battery_capacity_to as number | null),
    powerFrom: formatPlainNumber(raw.power_from as number | null),
    powerTo: formatPlainNumber(raw.power_to as number | null),
  };
}

const COMPARE_KEYS: (keyof BackendSearchFilters)[] = [
  "brand",
  "model",
  "year_from",
  "year_to",
  "price_from",
  "price_to",
  "currency",
  "mileage_from",
  "mileage_to",
  "fuel",
  "transmission",
  "region",
  "sources",
  "category",
  "engine_volume_from",
  "engine_volume_to",
  "drivetrain",
  "colors",
  "fuel_consumption_from",
  "fuel_consumption_to",
  "ev_range_from",
  "ev_range_to",
  "battery_capacity_from",
  "battery_capacity_to",
  "power_from",
  "power_to",
];

function normalizeCompareSlice(filters: BackendSearchFilters): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const key of COMPARE_KEYS) {
    let value = filters[key];
    if (value === null || value === undefined || value === "") continue;
    if (Array.isArray(value)) {
      const sorted = [...value].map(String).sort();
      if (sorted.length === 0) continue;
      out[key] = sorted;
      continue;
    }
    if (key === "category" && (value === "all" || value === null)) continue;
    out[key] = value;
  }
  if (!out.currency) out.currency = "USD";
  return out;
}

/** Чи збігаються фільтри моніторингу з поточним пошуком (без урахування назви). */
export function searchFiltersMatchUi(
  stored: Record<string, unknown> | null | undefined,
  uiFilters: SearchFilterState,
): boolean {
  const fromUi = normalizeCompareSlice(toBackendSearchFilters(uiFilters));
  const fromStored = normalizeCompareSlice(
    toBackendSearchFilters(fromBackendSearchFilters(stored)),
  );
  return JSON.stringify(fromUi) === JSON.stringify(fromStored);
}

export function findMatchingSearch(
  searches: { id: string; filters: Record<string, unknown> }[],
  uiFilters: SearchFilterState,
): { id: string; filters: Record<string, unknown> } | null {
  for (const search of searches) {
    if (searchFiltersMatchUi(search.filters, uiFilters)) return search;
  }
  return null;
}

export function buildSearchName(filters: SearchFilterState): string {
  const custom = filters.name.trim();
  if (custom) return custom;

  const parts: string[] = [];
  if (filters.brand) parts.push(filters.brand);
  if (filters.model) parts.push(filters.model);
  if (parts.length === 0) parts.push("Мій пошук");
  if (filters.region && filters.region !== "Вся Україна") {
    parts.push(filters.region.replace(/^м\.\s*/i, ""));
  }
  return parts.join(" · ");
}
