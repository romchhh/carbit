import type { ExportListing } from "@/lib/export-listings";
import type { Listing } from "@/types/api";
import {
  NEW_CAR_MILEAGE_MAX_KM,
  NEW_CAR_YEAR_MAX,
  NEW_CAR_YEAR_MIN,
} from "@/lib/listing-source";
import { regionMatchesListing } from "@/lib/search-data/regions";
import { resolveDisplayCurrency, resolveListingCurrency, toUah } from "@/lib/display-currency";

export type SearchResult = ExportListing & {
  id: string;
  risk: string;
  brand: string;
  model: string;
};

export type VehicleCategory = "all" | "used" | "new" | "import";

export type TriFilterValue = "" | "show" | "hide";
export type SellerFilterValue = "" | "private" | "dealer";
export type AccidentFilterValue = "" | "none" | "had";
export type OwnersFilterValue = "" | "1" | "2" | "3" | "4";
export type PublishedWithinDaysValue = "" | "1" | "3" | "7" | "14" | "30";

export type SearchFilterState = {
  name: string;
  category: VehicleCategory;
  vehicleType: string;
  region: string;
  brand: string;
  model: string;
  /** @deprecated лише для сумісності API — завжди 0–1 значення */
  brands: string[];
  /** @deprecated лише для сумісності API — завжди 0–1 значення */
  models: string[];
  /** @deprecated лише для сумісності API — завжди 0–1 значення */
  regions: string[];
  yearFrom: string;
  yearTo: string;
  priceFrom: string;
  priceTo: string;
  /** Валюта діапазону ціни */
  currency: "USD" | "UAH" | "EUR";
  mileageFrom: string;
  mileageTo: string;
  fuels: string[];
  transmissions: string[];
  sources: string[];
  engineVolumeFrom: string;
  engineVolumeTo: string;
  driveTypes: string[];
  colors: string[];
  fuelConsumptionFrom: string;
  fuelConsumptionTo: string;
  rangeFrom: string;
  rangeTo: string;
  batteryCapacityFrom: string;
  batteryCapacityTo: string;
  powerFrom: string;
  powerTo: string;
  seatsFrom: string;
  seatsTo: string;
  bodyTypes: string[];
  doorsFrom: string;
  doorsTo: string;
  sellerFilter: SellerFilterValue;
  accident: AccidentFilterValue;
  zeroMileage: boolean;
  bargain: boolean;
  vinVerified: boolean;
  ownersMax: OwnersFilterValue;
  inCredit: TriFilterValue;
  usaImport: TriFilterValue;
  notCustoms: TriFilterValue;
  metallic: boolean;
  powerUnit: "hp" | "kw";
  /** Оголошення, додані за останні N днів (порожньо = без обмеження). */
  publishedWithinDays: PublishedWithinDaysValue;
  /** Кастомний діапазон публікації (datetime-local). */
  publishedFrom: string;
  publishedTo: string;
};

export type SortOption =
  | "newest"
  | "published_asc"
  | "price_asc"
  | "price_desc"
  | "year_desc"
  | "mileage_asc";

export const FUEL_OPTIONS = [
  "Бензин",
  "Дизель",
  "Електро",
  "Газ",
  "Газ пропан+бензин",
  "Газ метан+бензин",
  "Гібрид",
] as const;
export const TRANSMISSION_OPTIONS = [
  "Механіка",
  "Автомат",
  "Типтронік",
  "Робот",
  "Варіатор",
  "Редуктор",
] as const;
export const BODY_TYPE_OPTIONS = [
  "Седан",
  "Універсал",
  "Хетчбек",
  "Купе",
  "Мінівен",
  "Позашляховик",
  "Кросовер",
  "Пікап",
  "Ліфтбек",
] as const;
export const SOURCE_OPTIONS = [
  "AUTO.RIA",
  "OLX",
  "Car Market",
  "Імперія Авто",
  "uDrive",
  "Telegram",
] as const;
export const DRIVE_OPTIONS = ["Передній", "Задній", "Повний"] as const;
export const COLOR_SWATCHES = [
  { name: "Білий", hex: "#F5F5F5", border: true },
  { name: "Чорний", hex: "#1A1A1A" },
  { name: "Сірий", hex: "#8A8F98" },
  { name: "Срібний", hex: "#C0C5CC" },
  { name: "Синій", hex: "#2F5BFF" },
  { name: "Червоний", hex: "#E11D2E" },
  { name: "Зелений", hex: "#1F8A4C" },
  { name: "Жовтий", hex: "#F5C518" },
  { name: "Помаранчевий", hex: "#F97316" },
  { name: "Коричневий", hex: "#7A4A2A" },
  { name: "Бежевий", hex: "#D9C3A3" },
  { name: "Фіолетовий", hex: "#7C3AED" },
] as const;

export const COLOR_OPTIONS = COLOR_SWATCHES.map(c => c.name);

export const COLOR_HEX_BY_NAME: Record<string, string> = Object.fromEntries(
  COLOR_SWATCHES.map(c => [c.name, c.hex]),
);

export const VEHICLE_TYPE_OPTIONS = ["Легкові", "Вантажні"] as const;

export const SELLER_FILTER_OPTIONS = [
  { value: "" as SellerFilterValue, label: "Всі" },
  { value: "private" as SellerFilterValue, label: "Приватна особа" },
  { value: "dealer" as SellerFilterValue, label: "Компанія" },
];

export const ACCIDENT_FILTER_OPTIONS = [
  { value: "" as AccidentFilterValue, label: "Всі" },
  { value: "none" as AccidentFilterValue, label: "Не був" },
  { value: "had" as AccidentFilterValue, label: "Був" },
];

export const OWNERS_FILTER_OPTIONS = [
  { value: "" as OwnersFilterValue, label: "Будь-яка" },
  { value: "1" as OwnersFilterValue, label: "1" },
  { value: "2" as OwnersFilterValue, label: "2" },
  { value: "3" as OwnersFilterValue, label: "3" },
  { value: "4" as OwnersFilterValue, label: "4+" },
];

export const PUBLISHED_WITHIN_OPTIONS = [
  { value: "" as PublishedWithinDaysValue, label: "Будь-коли" },
  { value: "1" as PublishedWithinDaysValue, label: "За 1 день" },
  { value: "3" as PublishedWithinDaysValue, label: "За 3 дні" },
  { value: "7" as PublishedWithinDaysValue, label: "За 7 днів" },
  { value: "14" as PublishedWithinDaysValue, label: "За 14 днів" },
  { value: "30" as PublishedWithinDaysValue, label: "За 30 днів" },
] as const;

export const PUBLISHED_WITHIN_LABELS = PUBLISHED_WITHIN_OPTIONS.filter(o => o.value).map(
  o => o.label,
);

export function publishedWithinDaysLabel(value: PublishedWithinDaysValue): string {
  return PUBLISHED_WITHIN_OPTIONS.find(o => o.value === value)?.label ?? "Будь-коли";
}

export function publishedWithinDaysFromLabel(label: string): PublishedWithinDaysValue {
  if (!label || label === "Будь-коли") return "";
  return PUBLISHED_WITHIN_OPTIONS.find(o => o.label === label)?.value ?? "";
}

export const CATEGORY_OPTIONS: { value: VehicleCategory; label: string }[] = [
  { value: "all", label: "Всі" },
  { value: "used", label: "Вживані" },
  { value: "new", label: "Нові · до 1000 км" },
  { value: "import", label: "Під пригон" },
];

export const PRICE_CURRENCY_OPTIONS = [
  { value: "USD" as const, label: "$", suffix: "$" },
  { value: "EUR" as const, label: "€", suffix: "€" },
  { value: "UAH" as const, label: "грн", suffix: "грн" },
] as const;

export const DEFAULT_PRICE_BY_CURRENCY = {
  USD: { from: "10 000", to: "22 000" },
  EUR: { from: "9 000", to: "20 000" },
  UAH: { from: "400 000", to: "900 000" },
} as const;

/** Підказки для placeholder — не підставляються як значення фільтра. */
export const YEAR_PLACEHOLDERS = { from: "2018", to: "2024" } as const;
export const YEAR_MIN = 1950;

export function yearMax(): number {
  return new Date().getFullYear() + 1;
}

export const DEFAULT_FILTERS: SearchFilterState = {
  name: "",
  category: "all",
  vehicleType: "Легкові",
  region: "м. Київ",
  brand: "",
  model: "",
  brands: [],
  models: [],
  regions: ["м. Київ"],
  yearFrom: "",
  yearTo: "",
  priceFrom: "",
  priceTo: "",
  currency: "USD",
  mileageFrom: "",
  mileageTo: "",
  fuels: [],
  transmissions: [],
  sources: [...SOURCE_OPTIONS],
  engineVolumeFrom: "",
  engineVolumeTo: "",
  driveTypes: [],
  colors: [],
  fuelConsumptionFrom: "",
  fuelConsumptionTo: "",
  rangeFrom: "",
  rangeTo: "",
  batteryCapacityFrom: "",
  batteryCapacityTo: "",
  powerFrom: "",
  powerTo: "",
  seatsFrom: "",
  seatsTo: "",
  bodyTypes: [],
  doorsFrom: "",
  doorsTo: "",
  sellerFilter: "",
  accident: "",
  zeroMileage: false,
  bargain: false,
  vinVerified: false,
  ownersMax: "",
  inCredit: "",
  usaImport: "",
  notCustoms: "",
  metallic: false,
  powerUnit: "hp",
  publishedWithinDays: "",
  publishedFrom: "",
  publishedTo: "",
};

export const CATALOG_LISTINGS: SearchResult[] = [
  { id: "1", brand: "Toyota", model: "Camry", title: "Toyota Camry 2.5 AT", year: 2021, mileage: 45000, price: 780000, region: "Київ", fuel: "Бензин", trans: "Автомат", src: "AUTO.RIA", time: "12 хв тому", desc: "Один власник, офіційний дилер. Без ДТП.", risk: "low" },
  { id: "2", brand: "Toyota", model: "Camry", title: "Toyota Camry 2.0 AT", year: 2019, mileage: 88000, price: 610000, region: "Київ", fuel: "Бензин", trans: "Автомат", src: "Telegram", time: "34 хв тому", desc: "Акуратна експлуатація. Торг доречний.", risk: "medium" },
  { id: "3", brand: "Toyota", model: "Camry", title: "Toyota Camry 3.5 AT", year: 2022, mileage: 31000, price: 890000, region: "Харків", fuel: "Бензин", trans: "Автомат", src: "OLX", time: "1 год тому", desc: "Максимальна комплектація, на гарантії.", risk: "low" },
  { id: "4", brand: "Toyota", model: "Camry", title: "Toyota Camry 2.5 Hybrid", year: 2020, mileage: 62000, price: 720000, region: "Одеса", fuel: "Гібрид", trans: "Автомат", src: "AUTO.RIA", time: "3 год тому", desc: "Економічний гібрид, сервісна книга.", risk: "medium" },
  { id: "5", brand: "Volkswagen", model: "Passat", title: "Volkswagen Passat 2.0 TDI", year: 2019, mileage: 112000, price: 620000, region: "Львів", fuel: "Дизель", trans: "Автомат", src: "OLX", time: "5 год тому", desc: "Highline, повна комплектація.", risk: "low" },
  { id: "6", brand: "Skoda", model: "Octavia", title: "Skoda Octavia 1.4 TSI", year: 2018, mileage: 98000, price: 485000, region: "Одеса", fuel: "Бензин", trans: "Робот", src: "Telegram", time: "6 год тому", desc: "Торг доречний, один власник.", risk: "medium" },
  { id: "7", brand: "BMW", model: "3 Series", title: "BMW 320i xDrive", year: 2020, mileage: 54000, price: 950000, region: "Київ", fuel: "Бензин", trans: "Автомат", src: "AUTO.RIA", time: "8 год тому", desc: "M Sport пакет, повна історія.", risk: "low" },
  { id: "8", brand: "Hyundai", model: "Sonata", title: "Hyundai Sonata 2.0", year: 2021, mileage: 41000, price: 680000, region: "Дніпро", fuel: "Бензин", trans: "Автомат", src: "OLX", time: "10 год тому", desc: "Premium комплектація.", risk: "low" },
  { id: "9", brand: "Honda", model: "Accord", title: "Honda Accord 2.4", year: 2018, mileage: 105000, price: 520000, region: "Вінниця", fuel: "Бензин", trans: "Автомат", src: "Telegram", time: "12 год тому", desc: "Надійний седан, без ДТП.", risk: "medium" },
  { id: "10", brand: "Toyota", model: "RAV4", title: "Toyota RAV4 2.5", year: 2023, mileage: 18000, price: 1150000, region: "Київ", fuel: "Бензин", trans: "Автомат", src: "AUTO.RIA", time: "15 хв тому", desc: "Новий кросовер, повний привід.", risk: "low" },
  { id: "11", brand: "Nissan", model: "Leaf", title: "Nissan Leaf 40 kWh", year: 2019, mileage: 67000, price: 430000, region: "Львів", fuel: "Електро", trans: "Автомат", src: "OLX", time: "1 дн тому", desc: "Електромобіль, батарея 85%.", risk: "medium" },
  { id: "12", brand: "Kia", model: "Sportage", title: "Kia Sportage 1.6 T-GDI", year: 2022, mileage: 35000, price: 820000, region: "Запоріжжя", fuel: "Бензин", trans: "Автомат", src: "Telegram", time: "2 дн тому", desc: "GT Line, панорама.", risk: "low" },
  { id: "13", brand: "Toyota", model: "Camry", title: "Toyota Camry 2.5 MT", year: 2017, mileage: 125000, price: 480000, region: "Харків", fuel: "Бензин", trans: "Механіка", src: "OLX", time: "2 дн тому", desc: "Бюджетний варіант для перепродажу.", risk: "high" },
  { id: "14", brand: "Mercedes-Benz", model: "C-Class", title: "Mercedes-Benz C 200", year: 2020, mileage: 58000, price: 980000, region: "Київ", fuel: "Бензин", trans: "Автомат", src: "AUTO.RIA", time: "3 дн тому", desc: "AMG Line, дилерський пробіг.", risk: "low" },
  { id: "15", brand: "Renault", model: "Megane", title: "Renault Megane 1.5 dCi", year: 2018, mileage: 92000, price: 390000, region: "Одеса", fuel: "Дизель", trans: "Механіка", src: "Telegram", time: "4 дн тому", desc: "Економічний дизель.", risk: "medium" },
];

export function parseNumberInput(value: string): number | null {
  const digits = value.replace(/\s/g, "").replace(/[^\d]/g, "");
  if (!digits) return null;
  const num = Number(digits);
  return Number.isFinite(num) ? num : null;
}

export function formatDecimalInput(value: string, maxDecimals = 1): string {
  const cleaned = value.replace(",", ".").replace(/[^\d.]/g, "");
  const [whole, ...rest] = cleaned.split(".");
  if (rest.length === 0) return whole;
  return `${whole}.${rest.join("").slice(0, maxDecimals)}`;
}

export function parseThousandsKm(value: string): number | null {
  const num = parseNumberInput(value);
  if (num == null) return null;
  return num * 1000;
}

export function formatPriceInput(value: string): string {
  const digits = value.replace(/[^\d]/g, "");
  if (!digits) return "";
  const num = Number(digits);
  if (!Number.isFinite(num)) return digits;
  return num.toLocaleString("uk-UA");
}

export function formatYearInput(value: string): string {
  const digits = value.replace(/[^\d]/g, "").slice(0, 4);
  if (digits.length < 4) return digits;
  const n = Number(digits);
  const max = yearMax();
  if (!Number.isFinite(n)) return "";
  if (n < YEAR_MIN) return String(YEAR_MIN);
  if (n > max) return String(max);
  return digits;
}

/** Після введення: обмежити межі і поміняти місцями, якщо «від» > «до». */
export function normalizeYearRange(from: string, to: string): { from: string; to: string } {
  let a = formatYearInput(from);
  let b = formatYearInput(to);
  const na = parseNumberInput(a);
  const nb = parseNumberInput(b);
  if (na != null && nb != null && na > nb) {
    return { from: String(nb), to: String(na) };
  }
  return { from: a, to: b };
}

export function normalizePriceRange(from: string, to: string): { from: string; to: string } {
  let a = formatPriceInput(from);
  let b = formatPriceInput(to);
  const na = parseNumberInput(a);
  const nb = parseNumberInput(b);
  if (na != null && nb != null && na > nb) {
    return { from: formatPriceInput(String(nb)), to: formatPriceInput(String(na)) };
  }
  return { from: a, to: b };
}

function regionMatches(listingRegion: string, filterRegion: string): boolean {
  return regionMatchesListing(listingRegion, filterRegion);
}

export function filterListings(items: SearchResult[], filters: SearchFilterState): SearchResult[] {
  const yearFrom = parseNumberInput(filters.yearFrom);
  const yearTo = parseNumberInput(filters.yearTo);
  const rawPriceFrom = parseNumberInput(filters.priceFrom);
  const rawPriceTo = parseNumberInput(filters.priceTo);
  const filterCur = resolveDisplayCurrency(filters.currency);
  const priceFrom =
    rawPriceFrom == null ? null : toUah(rawPriceFrom, filterCur);
  const priceTo = rawPriceTo == null ? null : toUah(rawPriceTo, filterCur);
  const mileageFrom = parseThousandsKm(filters.mileageFrom) ?? parseNumberInput(filters.mileageFrom);
  const mileageTo = parseThousandsKm(filters.mileageTo) ?? parseNumberInput(filters.mileageTo);

  const brands = filters.brands.length ? filters.brands : filters.brand ? [filters.brand] : [];
  const models = filters.models.length ? filters.models : filters.model ? [filters.model] : [];
  const regions =
    filters.regions.length > 0
      ? filters.regions
      : filters.region && filters.region !== "Вся Україна"
        ? [filters.region]
        : [];

  return items.filter(item => {
    if (brands.length && !brands.includes(item.brand)) return false;
    if (models.length && !models.includes(item.model)) return false;
    if (regions.length && !regions.some(r => regionMatches(item.region, r))) return false;
    if (yearFrom != null && item.year < yearFrom) return false;
    if (yearTo != null && item.year > yearTo) return false;
    const itemUah = toUah(item.price, resolveListingCurrency((item as { currency?: string }).currency));
    if (priceFrom != null && itemUah < priceFrom) return false;
    if (priceTo != null && itemUah > priceTo) return false;
    if (mileageFrom != null && item.mileage < mileageFrom) return false;
    if (mileageTo != null && item.mileage > mileageTo) return false;
    if (filters.fuels.length > 0 && item.fuel && !filters.fuels.includes(item.fuel)) return false;
    if (filters.transmissions.length > 0 && item.trans && !filters.transmissions.includes(item.trans)) return false;
    if (filters.sources.length > 0 && !filters.sources.includes(item.src)) return false;
    if (filters.category && filters.category !== "all") {
      const desc = `${item.title} ${item.desc ?? ""}`.toLowerCase();
      const isImport = /пригон|нерозмит|єврономер|еврономер/.test(desc);
      const fromUdrive =
        item.id.startsWith("udrive_") || item.src === "uDrive";
      const fromNewAutoRia = item.id.startsWith("new_auto_ria_");
      const yearOk =
        item.year >= NEW_CAR_YEAR_MIN && item.year <= NEW_CAR_YEAR_MAX;
      const isNewMileage = item.mileage <= NEW_CAR_MILEAGE_MAX_KM;
      const isNew = fromUdrive || (yearOk && isNewMileage);
      if (filters.category === "import" && (fromUdrive || fromNewAutoRia || !isImport))
        return false;
      if (filters.category === "new") {
        if (!isNew) return false;
        if (!fromUdrive && !fromNewAutoRia && (isImport || item.mileage > 1000))
          return false;
      }
      if (filters.category === "used" && (isImport || isNew)) return false;
    }
    return true;
  });
}

export function sortListings(items: SearchResult[], sort: SortOption): SearchResult[] {
  const sorted = [...items];
  switch (sort) {
    case "price_asc":
      return sorted.sort((a, b) => a.price - b.price);
    case "price_desc":
      return sorted.sort((a, b) => b.price - a.price);
    case "year_desc":
      return sorted.sort((a, b) => b.year - a.year);
    case "mileage_asc":
      return sorted.sort((a, b) => a.mileage - b.mileage);
    case "newest":
      return sorted.sort((a, b) => {
        const sortMs = (item: SearchResult) => {
          for (const raw of [item.refreshedAt, item.publishedAt, item.foundAt]) {
            const t = Date.parse(raw || "");
            if (Number.isFinite(t) && t > 0) return t;
          }
          return 0;
        };
        return sortMs(b) - sortMs(a);
      });
    case "published_asc":
      return sorted.sort((a, b) => {
        const sortMs = (item: SearchResult) => {
          for (const raw of [item.refreshedAt, item.publishedAt, item.foundAt]) {
            const t = Date.parse(raw || "");
            if (Number.isFinite(t) && t > 0) return t;
          }
          return 0;
        };
        return sortMs(a) - sortMs(b);
      });
    default:
      return sorted;
  }
}

/** Сортування вже завантажених карток live-пошуку без нового запиту до API. */
export function sortListingItems(items: Listing[], sort: SortOption): Listing[] {
  const sorted = [...items];
  const priceUah = (item: Listing) =>
    toUah(item.price, resolveListingCurrency(item.currency));
  const publishedMs = (item: Listing) => {
    for (const raw of [
      item.refreshed_at,
      (item as Listing & { refreshedAt?: string }).refreshedAt,
      item.published_at,
      (item as Listing & { publishedAt?: string }).publishedAt,
      item.found_at,
      (item as Listing & { foundAt?: string }).foundAt,
    ]) {
      const t = Date.parse(raw || "");
      if (Number.isFinite(t) && t > 0) return t;
    }
    return 0;
  };

  switch (sort) {
    case "price_asc":
      return sorted.sort((a, b) => priceUah(a) - priceUah(b));
    case "price_desc":
      return sorted.sort((a, b) => priceUah(b) - priceUah(a));
    case "year_desc":
      return sorted.sort((a, b) => (b.year || 0) - (a.year || 0));
    case "mileage_asc":
      return sorted.sort((a, b) => (a.mileage || 0) - (b.mileage || 0));
    case "published_asc":
      return sorted.sort((a, b) => publishedMs(a) - publishedMs(b));
    default:
      return sorted.sort((a, b) => publishedMs(b) - publishedMs(a));
  }
}

export function toggleValue(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter(v => v !== value) : [...list, value];
}

function fieldActive(value: string | boolean | undefined): boolean {
  if (typeof value === "boolean") return value;
  return Boolean(value && String(value).trim());
}

export function countAdvancedFilterFields(
  filters: SearchFilterState,
  section: "technical" | "condition" | "origin",
): number {
  if (section === "technical") {
    return [
      filters.bodyTypes.length,
      filters.fuels.length,
      filters.transmissions.length,
      fieldActive(filters.mileageFrom),
      fieldActive(filters.mileageTo),
      filters.zeroMileage,
      fieldActive(filters.engineVolumeFrom),
      fieldActive(filters.engineVolumeTo),
      filters.driveTypes.length,
      filters.colors.length,
      filters.metallic,
      fieldActive(filters.fuelConsumptionFrom),
      fieldActive(filters.fuelConsumptionTo),
      fieldActive(filters.rangeFrom),
      fieldActive(filters.rangeTo),
      fieldActive(filters.batteryCapacityFrom),
      fieldActive(filters.batteryCapacityTo),
      fieldActive(filters.powerFrom),
      fieldActive(filters.powerTo),
      fieldActive(filters.seatsFrom),
      fieldActive(filters.seatsTo),
      fieldActive(filters.doorsFrom),
      fieldActive(filters.doorsTo),
    ].filter(Boolean).length;
  }
  if (section === "condition") {
    return [
      fieldActive(filters.accident),
      fieldActive(filters.sellerFilter),
      fieldActive(filters.ownersMax),
      filters.vinVerified,
      filters.bargain,
      fieldActive(filters.inCredit),
      fieldActive(filters.publishedWithinDays),
      fieldActive(filters.publishedFrom),
      fieldActive(filters.publishedTo),
    ].filter(Boolean).length;
  }
  return [fieldActive(filters.usaImport), fieldActive(filters.notCustoms)].filter(Boolean).length;
}
