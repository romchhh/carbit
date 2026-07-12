import type { SearchFilterState } from "@/lib/search-catalog";

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
