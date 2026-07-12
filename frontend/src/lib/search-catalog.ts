import type { ExportListing } from "@/lib/export-listings";
import { regionMatchesListing } from "@/lib/search-data/regions";

export type SearchResult = ExportListing & {
  id: string;
  risk: string;
  brand: string;
  model: string;
};

export type VehicleCategory = "all" | "used" | "new" | "import";

export type SearchFilterState = {
  name: string;
  category: VehicleCategory;
  vehicleType: string;
  region: string;
  brand: string;
  model: string;
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
};

export type SortOption = "newest" | "price_asc" | "price_desc" | "year_desc" | "mileage_asc";

export const FUEL_OPTIONS = ["Бензин", "Дизель", "Гібрид", "Електро", "Газ"] as const;
export const TRANSMISSION_OPTIONS = ["Автомат", "Механіка", "Робот"] as const;
export const SOURCE_OPTIONS = ["AUTO.RIA", "OLX", "Telegram"] as const;
export const DRIVE_OPTIONS = ["Передній", "Задній", "Повний"] as const;
export const COLOR_OPTIONS = [
  "Білий", "Чорний", "Сірий", "Срібний", "Синій", "Червоний",
  "Зелений", "Жовтий", "Помаранчевий", "Коричневий", "Бежевий", "Фіолетовий",
] as const;

export const VEHICLE_TYPE_OPTIONS = ["Легкові", "Мото", "Вантажні", "Причепи", "Автобуси", "Сільгосп", "Спецтехніка"] as const;

export const CATEGORY_OPTIONS: { value: VehicleCategory; label: string }[] = [
  { value: "all", label: "Всі" },
  { value: "used", label: "Вживані" },
  { value: "new", label: "Нові" },
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

export const DEFAULT_FILTERS: SearchFilterState = {
  name: "",
  category: "all",
  vehicleType: "Легкові",
  region: "м. Київ",
  brand: "",
  model: "",
  yearFrom: "2018",
  yearTo: "2024",
  priceFrom: DEFAULT_PRICE_BY_CURRENCY.USD.from,
  priceTo: DEFAULT_PRICE_BY_CURRENCY.USD.to,
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
  const num = parseNumberInput(value);
  if (num == null) return value.replace(/[^\d]/g, "");
  return num.toLocaleString("uk-UA");
}

function regionMatches(listingRegion: string, filterRegion: string): boolean {
  return regionMatchesListing(listingRegion, filterRegion);
}

export function filterListings(items: SearchResult[], filters: SearchFilterState): SearchResult[] {
  const yearFrom = parseNumberInput(filters.yearFrom);
  const yearTo = parseNumberInput(filters.yearTo);
  const rawPriceFrom = parseNumberInput(filters.priceFrom);
  const rawPriceTo = parseNumberInput(filters.priceTo);
  const usdToUah = 45;
  const eurToUah = 44;
  const priceFrom =
    rawPriceFrom == null
      ? null
      : filters.currency === "USD"
        ? rawPriceFrom * usdToUah
        : filters.currency === "EUR"
          ? rawPriceFrom * eurToUah
          : rawPriceFrom;
  const priceTo =
    rawPriceTo == null
      ? null
      : filters.currency === "USD"
        ? rawPriceTo * usdToUah
        : filters.currency === "EUR"
          ? rawPriceTo * eurToUah
          : rawPriceTo;
  const mileageFrom = parseThousandsKm(filters.mileageFrom) ?? parseNumberInput(filters.mileageFrom);
  const mileageTo = parseThousandsKm(filters.mileageTo) ?? parseNumberInput(filters.mileageTo);

  return items.filter(item => {
    if (filters.brand && item.brand !== filters.brand) return false;
    if (filters.model && item.model !== filters.model) return false;
    if (!regionMatches(item.region, filters.region)) return false;
    if (yearFrom != null && item.year < yearFrom) return false;
    if (yearTo != null && item.year > yearTo) return false;
    if (priceFrom != null && item.price < priceFrom) return false;
    if (priceTo != null && item.price > priceTo) return false;
    if (mileageFrom != null && item.mileage < mileageFrom) return false;
    if (mileageTo != null && item.mileage > mileageTo) return false;
    if (filters.fuels.length > 0 && item.fuel && !filters.fuels.includes(item.fuel)) return false;
    if (filters.transmissions.length > 0 && item.trans && !filters.transmissions.includes(item.trans)) return false;
    if (filters.sources.length > 0 && !filters.sources.includes(item.src)) return false;
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
    default:
      return sorted;
  }
}

export function toggleValue(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter(v => v !== value) : [...list, value];
}
