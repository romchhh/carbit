/** Курси — оновлюються з /fx/rates (НБУ); fallback як у backend. */
export let USD_TO_UAH = 45;
export let EUR_TO_UAH = 44;

let ratesLoadedAt = 0;
const RATES_TTL_MS = 60 * 60 * 1000;

export function applyFxRates(rates: { USD?: number; EUR?: number }) {
  if (rates.USD && rates.USD > 0) USD_TO_UAH = rates.USD;
  if (rates.EUR && rates.EUR > 0) EUR_TO_UAH = rates.EUR;
  ratesLoadedAt = Date.now();
}

export function fxRatesStale(): boolean {
  return !ratesLoadedAt || Date.now() - ratesLoadedAt > RATES_TTL_MS;
}

export type DisplayCurrency = "UAH" | "USD" | "EUR";

export const DEFAULT_DISPLAY_CURRENCY: DisplayCurrency = "USD";

export const DISPLAY_CURRENCY_OPTIONS: {
  value: DisplayCurrency;
  label: string;
  suffix: string;
}[] = [
  { value: "USD", label: "Долар", suffix: "$" },
  { value: "UAH", label: "Гривня", suffix: "грн" },
  { value: "EUR", label: "Євро", suffix: "€" },
];

export function resolveDisplayCurrency(value: string | null | undefined): DisplayCurrency {
  if (!value) return DEFAULT_DISPLAY_CURRENCY;
  const cur = value.toUpperCase();
  if (cur === "USD" || cur === "EUR" || cur === "UAH") return cur;
  if (cur === "ГРН" || cur === "UA") return "UAH";
  if (cur === "$" || cur === "US") return "USD";
  if (cur === "€" || cur === "EU" || cur === "EURO") return "EUR";
  return DEFAULT_DISPLAY_CURRENCY;
}

/** Валюта суми оголошення. Порожнє = грн (старі записи в БД). */
export function resolveListingCurrency(value: string | null | undefined): DisplayCurrency {
  if (!value) return "UAH";
  return resolveDisplayCurrency(value);
}

export function currencySuffix(currency: DisplayCurrency): string {
  if (currency === "USD") return "$";
  if (currency === "EUR") return "€";
  return "грн";
}

export function toUah(amount: number, from: DisplayCurrency): number {
  const value = Number(amount) || 0;
  if (from === "USD") return Math.round(value * USD_TO_UAH);
  if (from === "EUR") return Math.round(value * EUR_TO_UAH);
  return Math.round(value);
}

export function fromUah(amountUah: number, target: DisplayCurrency): number {
  const value = Number(amountUah) || 0;
  if (target === "USD") return Math.round(value / USD_TO_UAH);
  if (target === "EUR") return Math.round(value / EUR_TO_UAH);
  return Math.round(value);
}

/** Без round-trip, якщо валюти збігаються. */
export function convertPrice(
  amount: number,
  fromCurrency: string | null | undefined,
  toCurrency: string | null | undefined,
): number {
  const from = resolveListingCurrency(fromCurrency);
  const to = resolveDisplayCurrency(toCurrency);
  if (from === to) return Math.round(Number(amount) || 0);
  return fromUah(toUah(Number(amount) || 0, from), to);
}

/** Парсить 12500 / "12 500" / "12\u00a0500" з AUTO.RIA source_data. */
export function parseMoneyAmount(value: unknown): number | null {
  if (value == null || value === "") return null;
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.round(value);
  }
  if (typeof value !== "string") return null;
  const cleaned = value.replace(/[\s\u00a0\u202f\u2009]/g, "").replace(",", ".");
  if (!cleaned) return null;
  const num = Number(cleaned);
  if (!Number.isFinite(num)) return null;
  return Math.round(num);
}

/**
 * Рідна сума з AUTO.RIA (UAH/USD/EUR на верхньому рівні або в prices[]).
 * Уникає грн→$ через фіксований курс, коли джерело вже дає долари.
 */
export function nativeAmountFromSourceData(
  sourceData: Record<string, unknown> | null | undefined,
  currency: DisplayCurrency,
): number | null {
  if (!sourceData) return null;

  const direct = parseMoneyAmount(sourceData[currency]);
  if (direct != null && direct > 0) return direct;

  const prices = sourceData.prices;
  if (!Array.isArray(prices)) return null;

  for (const entry of prices) {
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) continue;
    const amount = parseMoneyAmount((entry as Record<string, unknown>)[currency]);
    if (amount != null && amount > 0) return amount;
  }
  return null;
}

export function formatListingPrice(
  amount: number,
  listingCurrency: string | null | undefined,
  preferredCurrency: DisplayCurrency | string | null | undefined = DEFAULT_DISPLAY_CURRENCY,
  sourceData?: Record<string, unknown> | null,
): string {
  const target = resolveDisplayCurrency(preferredCurrency);

  // 1) Рідна сума вже в потрібній валюті (AUTO.RIA source_data.USD / UAH / EUR)
  const nativeTarget = nativeAmountFromSourceData(sourceData, target);
  if (nativeTarget != null && nativeTarget > 0) {
    return `${new Intl.NumberFormat("uk-UA").format(nativeTarget)} ${currencySuffix(target)}`;
  }

  // 2) Конвертація з рідної суми джерела або з listing.price
  const from = resolveListingCurrency(listingCurrency);
  const nativeFrom = nativeAmountFromSourceData(sourceData, from);
  const raw = nativeFrom != null && nativeFrom > 0 ? nativeFrom : Number(amount) || 0;
  const value = convertPrice(raw, from, target);
  return `${new Intl.NumberFormat("uk-UA").format(value)} ${currencySuffix(target)}`;
}

/** @deprecated використовуй formatListingPrice з валютою оголошення */
export function formatPriceFromUah(
  amountUah: number,
  target: DisplayCurrency | string | null | undefined = DEFAULT_DISPLAY_CURRENCY,
): string {
  return formatListingPrice(amountUah, "UAH", target);
}
