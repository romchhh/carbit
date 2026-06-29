import type { SearchFilterState } from "@/lib/search-catalog";

export type BackendSearchFilters = {
  brand?: string | null;
  model?: string | null;
  year_from?: number | null;
  year_to?: number | null;
  price_from?: number | null;
  price_to?: number | null;
  mileage_from?: number | null;
  mileage_to?: number | null;
  fuel?: string[] | null;
  transmission?: string[] | null;
  region?: string | null;
  sources?: string[] | null;
};

function parseNumber(value: string): number | null {
  const digits = value.replace(/[^\d]/g, "");
  if (!digits) return null;
  const num = Number(digits);
  return Number.isFinite(num) ? num : null;
}

function parseThousandsKm(value: string): number | null {
  const num = parseNumber(value);
  if (num == null) return null;
  return num * 1000;
}

export function toBackendSearchFilters(filters: SearchFilterState): BackendSearchFilters {
  return {
    brand: filters.brand || null,
    model: filters.model || null,
    year_from: parseNumber(filters.yearFrom),
    year_to: parseNumber(filters.yearTo),
    price_from: parseNumber(filters.priceFrom),
    price_to: parseNumber(filters.priceTo),
    mileage_from: parseThousandsKm(filters.mileageFrom),
    mileage_to: parseThousandsKm(filters.mileageTo),
    fuel: filters.fuels.length ? [...filters.fuels] : null,
    transmission: filters.transmissions.length ? [...filters.transmissions] : null,
    region: filters.region || null,
    sources: ["auto_ria"],
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
