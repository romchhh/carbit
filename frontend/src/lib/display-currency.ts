/** Курси як у backend/app/services/currency.py — лише для крос-конвертації. */
export const USD_TO_UAH = 45;
export const EUR_TO_UAH = 44;

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

export function formatListingPrice(
  amount: number,
  listingCurrency: string | null | undefined,
  preferredCurrency: DisplayCurrency | string | null | undefined = DEFAULT_DISPLAY_CURRENCY,
): string {
  const target = resolveDisplayCurrency(preferredCurrency);
  const value = convertPrice(amount, listingCurrency, target);
  const formatted = new Intl.NumberFormat("uk-UA").format(value);
  return `${formatted} ${currencySuffix(target)}`;
}

/** @deprecated використовуй formatListingPrice з валютою оголошення */
export function formatPriceFromUah(
  amountUah: number,
  target: DisplayCurrency | string | null | undefined = DEFAULT_DISPLAY_CURRENCY,
): string {
  return formatListingPrice(amountUah, "UAH", target);
}
