import type {
  AccidentFilterValue,
  OwnersFilterValue,
  SearchFilterState,
  SellerFilterValue,
  TriFilterValue,
} from "@/lib/search-catalog";
import { DEFAULT_FILTERS } from "@/lib/search-catalog";
import {
  effectiveBrands,
  effectiveModels,
  effectiveRegions,
  syncSearchFilterArrays,
} from "@/lib/search-filter-multi";

export type BackendSearchFilters = {
  brand?: string | null;
  model?: string | null;
  brands?: string[] | null;
  models?: string[] | null;
  regions?: string[] | null;
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
  seats_from?: number | null;
  seats_to?: number | null;
  doors_from?: number | null;
  doors_to?: number | null;
  body_types?: string[] | null;
  seller_filter?: string | null;
  accident?: string | null;
  zero_mileage?: boolean | null;
  bargain?: boolean | null;
  vin_verified?: boolean | null;
  owners_max?: number | null;
  in_credit?: string | null;
  usa_import?: string | null;
  not_customs?: string | null;
  metallic?: boolean | null;
  power_unit?: string | null;
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

function mapTri(value: TriFilterValue): string | null {
  if (!value) return null;
  return value;
}

function mapSources(sources: string[]): string[] | null {
  const mapped = sources
    .map(source => SOURCE_TO_BACKEND[source])
    .filter((source): source is string => Boolean(source));

  return mapped.length ? mapped : null;
}

function parseOwnersMax(value: OwnersFilterValue): number | null {
  if (!value) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export function toBackendSearchFilters(filters: SearchFilterState): BackendSearchFilters {
  const synced = syncSearchFilterArrays(filters);
  const brands = effectiveBrands(synced);
  const models = effectiveModels(synced);
  const regions = effectiveRegions(synced);
  const mileageFrom = synced.zeroMileage ? 0 : parseThousandsKm(synced.mileageFrom);
  const mileageTo = synced.zeroMileage ? 500 : parseThousandsKm(synced.mileageTo);

  return {
    brand: brands[0] || null,
    model: models[0] || null,
    brands: brands.length ? brands : null,
    models: models.length ? models : null,
    regions: regions.length ? regions : null,
    year_from: parseNumber(synced.yearFrom),
    year_to: parseNumber(synced.yearTo),
    price_from: parseNumber(synced.priceFrom),
    price_to: parseNumber(synced.priceTo),
    currency: synced.currency || "USD",
    mileage_from: mileageFrom,
    mileage_to: mileageTo,
    fuel: synced.fuels.length ? [...synced.fuels] : null,
    transmission: synced.transmissions.length ? [...synced.transmissions] : null,
    region: regions.length === 1 ? regions[0] : regions.length ? null : synced.region || null,
    sources: mapSources(synced.sources),
    category: synced.category !== "all" ? synced.category : null,
    engine_volume_from: parseDecimal(synced.engineVolumeFrom),
    engine_volume_to: parseDecimal(synced.engineVolumeTo),
    drivetrain: synced.driveTypes.length ? [...synced.driveTypes] : null,
    colors: synced.colors.length ? [...synced.colors] : null,
    fuel_consumption_from: parseDecimal(synced.fuelConsumptionFrom),
    fuel_consumption_to: parseDecimal(synced.fuelConsumptionTo),
    ev_range_from: parseNumber(synced.rangeFrom),
    ev_range_to: parseNumber(synced.rangeTo),
    battery_capacity_from: parseDecimal(synced.batteryCapacityFrom),
    battery_capacity_to: parseDecimal(synced.batteryCapacityTo),
    power_from: parseNumber(synced.powerFrom),
    power_to: parseNumber(synced.powerTo),
    seats_from: parseNumber(synced.seatsFrom),
    seats_to: parseNumber(synced.seatsTo),
    doors_from: parseNumber(synced.doorsFrom),
    doors_to: parseNumber(synced.doorsTo),
    body_types: synced.bodyTypes.length ? [...synced.bodyTypes] : null,
    seller_filter: (synced.sellerFilter || null) as SellerFilterValue | null,
    accident: (synced.accident || null) as AccidentFilterValue | null,
    zero_mileage: synced.zeroMileage || null,
    bargain: synced.bargain || null,
    vin_verified: synced.vinVerified || null,
    owners_max: parseOwnersMax(synced.ownersMax),
    in_credit: mapTri(synced.inCredit),
    usa_import: mapTri(synced.usaImport),
    not_customs: mapTri(synced.notCustoms),
    metallic: synced.metallic || null,
    power_unit: synced.powerUnit || "hp",
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

function ownersToUi(value: number | null | undefined): OwnersFilterValue {
  if (value == null) return "";
  if (value >= 4) return "4";
  return String(value) as OwnersFilterValue;
}

/** Застосовує лише поля, які повернув AI (не скидає решту фільтрів). */
export function mergeAiSearchFilters(
  current: SearchFilterState,
  raw: Record<string, unknown> | null | undefined,
): SearchFilterState {
  if (!raw || typeof raw !== "object" || Object.keys(raw).length === 0) return current;

  const parsed = fromBackendSearchFilters(raw);
  const next = { ...current };

  if (raw.brand != null && String(raw.brand).trim()) {
    next.brand = parsed.brand;
    next.brands = parsed.brands;
    next.model = raw.model != null && String(raw.model).trim() ? parsed.model : "";
    next.models = next.model ? parsed.models : [];
  } else if (Array.isArray(raw.brands) && raw.brands.length) {
    next.brands = parsed.brands;
    next.brand = parsed.brand;
    next.models = parsed.models;
    next.model = parsed.model;
  } else if (raw.model != null && String(raw.model).trim()) {
    next.model = parsed.model;
    next.models = parsed.models;
  } else if (Array.isArray(raw.models) && raw.models.length) {
    next.models = parsed.models;
    next.model = parsed.model;
  }

  if (raw.category != null && String(raw.category).trim() && raw.category !== "all") {
    next.category = parsed.category;
  }
  if (raw.region != null && String(raw.region).trim()) {
    next.region = parsed.region;
    next.regions = parsed.regions;
  } else if (Array.isArray(raw.regions) && raw.regions.length) {
    next.regions = parsed.regions;
    next.region = parsed.region;
  }
  if (raw.year_from != null) next.yearFrom = parsed.yearFrom;
  if (raw.year_to != null) next.yearTo = parsed.yearTo;
  if (raw.price_from != null) next.priceFrom = parsed.priceFrom;
  if (raw.price_to != null) next.priceTo = parsed.priceTo;
  if (raw.currency != null && String(raw.currency).trim()) next.currency = parsed.currency;
  if (raw.mileage_from != null) next.mileageFrom = parsed.mileageFrom;
  if (raw.mileage_to != null) next.mileageTo = parsed.mileageTo;
  if (Array.isArray(raw.fuel) && raw.fuel.length) next.fuels = parsed.fuels;
  if (Array.isArray(raw.transmission) && raw.transmission.length) next.transmissions = parsed.transmissions;
  if (Array.isArray(raw.drivetrain) && raw.drivetrain.length) next.driveTypes = parsed.driveTypes;
  if (Array.isArray(raw.body_types) && raw.body_types.length) next.bodyTypes = parsed.bodyTypes;
  if (Array.isArray(raw.colors) && raw.colors.length) next.colors = parsed.colors;
  if (Array.isArray(raw.sources) && raw.sources.length) next.sources = parsed.sources;
  if (raw.engine_volume_from != null) next.engineVolumeFrom = parsed.engineVolumeFrom;
  if (raw.engine_volume_to != null) next.engineVolumeTo = parsed.engineVolumeTo;
  if (raw.power_from != null) next.powerFrom = parsed.powerFrom;
  if (raw.power_to != null) next.powerTo = parsed.powerTo;
  if (raw.seller_filter != null && String(raw.seller_filter).trim()) next.sellerFilter = parsed.sellerFilter;
  if (raw.accident != null && String(raw.accident).trim()) next.accident = parsed.accident;
  if (raw.zero_mileage === true) next.zeroMileage = true;
  if (raw.bargain === true) next.bargain = true;
  if (raw.vin_verified === true) next.vinVerified = true;
  if (raw.owners_max != null) next.ownersMax = parsed.ownersMax;
  if (raw.in_credit != null && String(raw.in_credit).trim()) next.inCredit = parsed.inCredit;
  if (raw.usa_import != null && String(raw.usa_import).trim()) next.usaImport = parsed.usaImport;
  if (raw.not_customs != null && String(raw.not_customs).trim()) next.notCustoms = parsed.notCustoms;
  if (raw.metallic === true) next.metallic = true;

  return next;
}

/** Повна заміна фільтрів голосовим запитом — попередній запит не зливається. */
export function applyVoiceSearchFilters(
  current: SearchFilterState,
  raw: Record<string, unknown>,
  options: {
    transcript?: string;
    marketDiscovery?: boolean;
    resolveBrand?: (query: string) => string | null;
    resolveModel?: (brand: string, query: string) => string | null;
    findBrandInText?: (text: string) => string | null;
    findModelInText?: (brand: string, text: string) => string | null;
  } = {},
): SearchFilterState {
  const parsed = fromBackendSearchFilters(raw);
  let merged = syncSearchFilterArrays({
    ...parsed,
    vehicleType: current.vehicleType,
  });

  const transcript = String(options.transcript || "").trim();
  let brand = merged.brand;
  let model = merged.model;

  if (raw.brand != null && String(raw.brand).trim() && options.resolveBrand) {
    brand = options.resolveBrand(String(raw.brand)) ?? String(raw.brand).trim();
  } else if (transcript && options.findBrandInText) {
    brand = options.findBrandInText(transcript) ?? "";
  } else if (!(raw.brand != null && String(raw.brand).trim())) {
    brand = "";
  }

  if (brand) {
    if (raw.model != null && String(raw.model).trim() && options.resolveModel) {
      model = options.resolveModel(brand, String(raw.model)) ?? String(raw.model).trim();
    } else if (transcript && options.findModelInText) {
      model = options.findModelInText(brand, transcript) ?? "";
    } else if (!(raw.model != null && String(raw.model).trim())) {
      model = "";
    }
    merged.brand = brand;
    merged.brands = [brand];
    merged.model = model;
    merged.models = model ? [model] : [];
  } else {
    merged.brand = "";
    merged.brands = [];
    merged.model = "";
    merged.models = [];
  }

  const hasRegion =
    (raw.region != null && String(raw.region).trim()) ||
    (Array.isArray(raw.regions) && raw.regions.length > 0);
  if (!hasRegion) {
    merged.region = "Вся Україна";
    merged.regions = [];
  } else {
    merged = syncSearchFilterArrays(merged);
  }

  if (options.marketDiscovery && !(raw.brand != null && String(raw.brand).trim()) && !brand) {
    merged.brand = "";
    merged.model = "";
    merged.brands = [];
    merged.models = [];
  }

  return syncSearchFilterArrays(merged);
}

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
  const sourcesMapped = sourcesRaw
    .map(s => BACKEND_SOURCE_TO_UI[s] || s)
    .filter(Boolean);
  const sources = sourcesMapped.length ? sourcesMapped : [...base.sources];

  const zeroMileage = Boolean(raw.zero_mileage);

  const fuelsRaw = Array.isArray(raw.fuel)
    ? raw.fuel
    : Array.isArray(raw.fuels)
      ? raw.fuels
      : null;
  const transmissionsRaw = Array.isArray(raw.transmission)
    ? raw.transmission
    : Array.isArray(raw.transmissions)
      ? raw.transmissions
      : null;
  const drivetrainRaw = Array.isArray(raw.drivetrain)
    ? raw.drivetrain
    : Array.isArray(raw.drive_types)
      ? raw.drive_types
      : null;

  const brandsRaw = Array.isArray(raw.brands) ? raw.brands.map(String).filter(Boolean) : [];
  const brand = String(raw.brand || brandsRaw[0] || "");
  const brands = brandsRaw.length ? brandsRaw : brand ? [brand] : [];

  const modelsRaw = Array.isArray(raw.models) ? raw.models.map(String).filter(Boolean) : [];
  const model = String(raw.model || modelsRaw[0] || "");
  const models = modelsRaw.length ? modelsRaw : model ? [model] : [];

  const regionsRaw = Array.isArray(raw.regions) ? raw.regions.map(String).filter(Boolean) : [];
  const regionLegacy = String(raw.region || "");
  const regions =
    regionsRaw.length > 0
      ? regionsRaw
      : regionLegacy && regionLegacy !== "Вся Україна"
        ? [regionLegacy]
        : [];
  const region =
    regions.length === 1 ? regions[0] : regions.length ? "" : regionLegacy || "Вся Україна";

  return {
    ...base,
    name: "",
    category: (["all", "used", "new", "import"].includes(category)
      ? category
      : "all") as SearchFilterState["category"],
    brand,
    model,
    brands,
    models,
    regions,
    region,
    yearFrom: formatPlainNumber(raw.year_from as number | null),
    yearTo: formatPlainNumber(raw.year_to as number | null),
    priceFrom: formatPlainNumber(raw.price_from as number | null),
    priceTo: formatPlainNumber(raw.price_to as number | null),
    currency,
    mileageFrom: zeroMileage ? "0" : formatThousandsKm(raw.mileage_from as number | null),
    mileageTo: zeroMileage ? "0" : formatThousandsKm(raw.mileage_to as number | null),
    fuels: fuelsRaw ? fuelsRaw.map(String) : [],
    transmissions: transmissionsRaw ? transmissionsRaw.map(String) : [],
    sources,
    engineVolumeFrom: formatPlainNumber(raw.engine_volume_from as number | null),
    engineVolumeTo: formatPlainNumber(raw.engine_volume_to as number | null),
    driveTypes: drivetrainRaw ? drivetrainRaw.map(String) : [],
    colors: Array.isArray(raw.colors) ? raw.colors.map(String) : [],
    fuelConsumptionFrom: formatPlainNumber(raw.fuel_consumption_from as number | null),
    fuelConsumptionTo: formatPlainNumber(raw.fuel_consumption_to as number | null),
    rangeFrom: formatPlainNumber(raw.ev_range_from as number | null),
    rangeTo: formatPlainNumber(raw.ev_range_to as number | null),
    batteryCapacityFrom: formatPlainNumber(raw.battery_capacity_from as number | null),
    batteryCapacityTo: formatPlainNumber(raw.battery_capacity_to as number | null),
    powerFrom: formatPlainNumber(raw.power_from as number | null),
    powerTo: formatPlainNumber(raw.power_to as number | null),
    seatsFrom: formatPlainNumber(raw.seats_from as number | null),
    seatsTo: formatPlainNumber(raw.seats_to as number | null),
    doorsFrom: formatPlainNumber(raw.doors_from as number | null),
    doorsTo: formatPlainNumber(raw.doors_to as number | null),
    bodyTypes: Array.isArray(raw.body_types) ? raw.body_types.map(String) : [],
    sellerFilter: (String(raw.seller_filter || "") || "") as SellerFilterValue,
    accident: (String(raw.accident || "") || "") as AccidentFilterValue,
    zeroMileage,
    bargain: Boolean(raw.bargain),
    vinVerified: Boolean(raw.vin_verified),
    ownersMax: ownersToUi(raw.owners_max as number | null),
    inCredit: (String(raw.in_credit || "") || "") as TriFilterValue,
    usaImport: (String(raw.usa_import || "") || "") as TriFilterValue,
    notCustoms: (String(raw.not_customs || "") || "") as TriFilterValue,
    metallic: Boolean(raw.metallic),
    powerUnit: raw.power_unit === "kw" ? "kw" : "hp",
  };
}

const COMPARE_KEYS: (keyof BackendSearchFilters)[] = [
  "brand",
  "model",
  "brands",
  "models",
  "regions",
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
  "seats_from",
  "seats_to",
  "doors_from",
  "doors_to",
  "body_types",
  "seller_filter",
  "accident",
  "zero_mileage",
  "bargain",
  "vin_verified",
  "owners_max",
  "in_credit",
  "usa_import",
  "not_customs",
  "metallic",
  "power_unit",
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
    if (typeof value === "boolean" && value === false) continue;
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

  const synced = syncSearchFilterArrays(filters);
  const brands = effectiveBrands(synced);
  const models = effectiveModels(synced);
  const regions = effectiveRegions(synced);

  const parts: string[] = [];
  if (brands.length === 1) parts.push(brands[0]);
  else if (brands.length > 1) parts.push(`${brands.length} марки`);
  if (models.length === 1) parts.push(models[0]);
  else if (models.length > 1) parts.push(`${models.length} моделі`);
  if (parts.length === 0) parts.push("Мій пошук");
  if (regions.length === 1) {
    parts.push(regions[0].replace(/^м\.\s*/i, ""));
  } else if (regions.length > 1) {
    parts.push(`${regions.length} регіони`);
  }
  return parts.join(" · ");
}

/** Скидає лише розширені поля, зберігаючи основний пошук. */
export function resetAdvancedFilters(filters: SearchFilterState): SearchFilterState {
  const keep: Pick<
    SearchFilterState,
    | "name"
    | "category"
    | "vehicleType"
    | "region"
    | "brand"
    | "model"
    | "brands"
    | "models"
    | "regions"
    | "yearFrom"
    | "yearTo"
    | "priceFrom"
    | "priceTo"
    | "currency"
    | "mileageFrom"
    | "mileageTo"
    | "sources"
  > = {
    name: filters.name,
    category: filters.category,
    vehicleType: filters.vehicleType,
    region: filters.region,
    brand: filters.brand,
    model: filters.model,
    brands: [...filters.brands],
    models: [...filters.models],
    regions: [...filters.regions],
    yearFrom: filters.yearFrom,
    yearTo: filters.yearTo,
    priceFrom: filters.priceFrom,
    priceTo: filters.priceTo,
    currency: filters.currency,
    mileageFrom: filters.mileageFrom,
    mileageTo: filters.mileageTo,
    sources: filters.sources,
  };
  return { ...DEFAULT_FILTERS, ...keep };
}
